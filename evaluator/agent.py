# -*- coding: utf-8 -*-
"""agent.py · 评价 Agent：多轮工具编排 + 确定性收口 + 轨迹留痕

链条：Agent 审查 → 输出四状态、证据链与分项评测分 → 由人决定如何采纳。
判定契约：四状态与证据链由 checker 内核机械收口；模型提 observations /
suggested_checks 与按课程评分框架 S1—S4 的分项评测分。评测分逐子项给、带理由与
证据引用，不是课程最终成绩，不进 verdict_digest。
HTML 中证据审查区与评测分区分开渲染。
"""

import json
import os
import uuid

from core import registry
from core.evidence import check_run_id, utc_now_iso
from .checker import Checker
from .contract import load_contract
from .fieldcheck import check_all as field_check_all, load_fields as load_field_spec
from .html_report import write_html
from .llm import chat, describe_model
from .precheck import precheck
from .tools import RestrictedTools

SKILL_DIR = os.path.join(os.path.dirname(__file__), 'skills', 'evidence-review')
VALID_STATUS = ('PASS', 'FAIL', 'INSUFFICIENT_EVIDENCE', 'NOT_APPLICABLE')


def _validate_scores(raw, max_by_id, valid_evidence_ids):
    """把模型给的评测分收成结构；非法项丢弃、越界不裁剪，不编造、不进判定。

    max_by_id 来自 rubric.evaluation_scoring.subcriteria（S1—S4 子项），
    内核不内置任何课程分值——换 rubric 就换评分框架。
    """
    out = {}
    if not isinstance(raw, list):
        return out
    for item in raw[:30]:
        if not isinstance(item, dict):
            continue
        sid = item.get('subcriterion_id') or item.get('criterion_id')
        if sid not in max_by_id:
            continue
        # 同一子项重复给分：已有合法分数保留第一个；
        # 已记录但分数非法时，允许后续合法条目覆盖，不让坏值占位。
        if sid in out and out[sid]['score'] is not None:
            continue
        score = item.get('score')
        if score is not None:
            try:
                score = int(score)
            except (TypeError, ValueError):
                score = None
            if score is not None and not (0 <= score <= int(max_by_id[sid])):
                score = None  # 越界直接丢弃，不裁剪成假分
        refs = [str(x) for x in (item.get('evidence_ids') or [])][:12]
        refs = [x for x in refs if x in valid_evidence_ids]
        level = str(item.get('evidence_level') or 'CLAIM_ONLY')
        if level not in ('CLAIM_ONLY', 'STATIC', 'OBSERVED', 'REPRODUCED'):
            level = 'CLAIM_ONLY'
        out[sid] = {
            'subcriterion_id': sid,
            'score': score,
            'max': int(max_by_id[sid]),
            'rationale': str(item.get('rationale') or '')[:600],
            'evidence_ids': refs,
            'evidence_level': level,
            'note': '分项评测分，非课程最终成绩；',
        }
    return out


def _decide(findings, report):
    """机械收口：确定性预检结果决定快照级状态。"""
    fails = [f for f in findings if f['level'] == 'FAIL']
    if fails:
        return 'FAIL', '确定性预检发现 %d 项阻断问题' % len(fails)
    if report is None:
        return 'FAIL', 'report.json 缺失'
    concl = report.get('conclusions', [])
    cov = report.get('coverage', {})
    checked = cov.get('checked', [])
    if not concl:
        if checked and not cov.get('decode_failed'):
            return 'PASS', '无命中结论（干净样本），覆盖声明完整（%d 项已检查）' % len(checked)
        return 'INSUFFICIENT_EVIDENCE', '报告无结论且覆盖声明不完整'
    if all(c.get('status') == registry.STATUS_UNDECIDED for c in concl):
        # 判点全量化后，「全部无法判定」有两种含义，必须分开判：
        #   有 missing_evidence → 规则没跑（数据源缺口）→ 弃权
        #   无 missing_evidence → 规则都跑了、机械未命中 → 干净样本，可判通过
        gaps = [c for c in concl if c.get('missing_evidence')]
        if gaps:
            return 'INSUFFICIENT_EVIDENCE', (
                '全部结论为「无法判定」（数据源缺口 %d 条）' % len(gaps))
        if checked and not cov.get('decode_failed'):
            return 'PASS', ('判点全部执行、机械未命中（干净样本），'
                            '覆盖声明完整（%d 项已检查）' % len(checked))
        return 'INSUFFICIENT_EVIDENCE', '无命中结论且覆盖声明不完整'
    insuff = [f for f in findings if f['level'] == 'INSUFFICIENT']
    if insuff:
        return 'INSUFFICIENT_EVIDENCE', insuff[0]['msg']
    return 'PASS', '引用、版本、结构检查通过（范围：%d 条结论）' % len(concl)


def evaluate_dir_quick(run_dir):
    """确定性快路径：供 K-1~K-6 校准判例与离线复算，不启动 Agent。"""
    findings, report, _records = precheck(run_dir)
    return _decide(findings, report)


def evaluate_run(project_root, run_id, use_llm=False):
    """兼容旧接口的确定性快路径；正式评价请走 run_agent。"""
    run_dir = os.path.join(project_root, 'evidence', check_run_id(run_id))
    if not os.path.isdir(run_dir):
        return {'run_id': run_id, 'status': 'FAIL', 'mode': 'deterministic',
                'findings': [{'level': 'FAIL', 'code': 'E-NO-RUN',
                              'msg': 'run 目录不存在：%s' % run_dir}],
                'text': '评价失败：run 目录不存在（%s）' % run_dir}
    findings, report, records = precheck(run_dir)
    status, reason = _decide(findings, report)
    lines = ['评价器快路径 · %s' % run_id, '- 状态：**%s**（%s）' % (status, reason),
             '- 模式：deterministic（机械核对，不含模型判读）',
             '- findings：%d 项' % len(findings)]
    return {'run_id': run_id, 'status': status, 'mode': 'deterministic',
            'reason': reason, 'llm_note': '', 'findings': findings,
            'evidence_records': len(records), 'text': '\n'.join(lines)}


class Budget(object):
    def __init__(self, max_model_calls=10, max_tests=5):
        self.model_calls = 0
        self.model_calls_max = max_model_calls
        self.tests_used = 0
        self.tests_max = max_tests
        self.exhausted_notes = []

    def consume_model(self):
        if self.model_calls >= self.model_calls_max:
            self.exhausted_notes.append('模型交互预算耗尽（%d 次）' % self.model_calls_max)
            return False
        self.model_calls += 1
        return True

    def consume_test(self):
        if self.tests_used >= self.tests_max:
            self.exhausted_notes.append('注册补测预算耗尽（%d 次）' % self.tests_max)
            return False
        self.tests_used += 1
        return True

    def as_dict(self):
        return {'model_calls_used': self.model_calls,
                'model_calls_max': self.model_calls_max,
                'registered_tests_used': self.tests_used,
                'registered_tests_max': self.tests_max,
                'exhausted_notes': list(self.exhausted_notes)}


def load_skill_and_rubric():
    with open(os.path.join(SKILL_DIR, 'SKILL.md'), 'r', encoding='utf-8') as f:
        skill = f.read()
    with open(os.path.join(SKILL_DIR, 'rubric.json'), 'r', encoding='utf-8') as f:
        rubric = json.load(f)
    return skill, rubric


def _parse_model_output(text):
    """容错解析：允许 ```json 包裹或前置说明文字。"""
    if not isinstance(text, str):
        return None
    cleaned = text.strip()
    if cleaned.startswith('```'):
        cleaned = cleaned.strip('`')
        if cleaned.lower().startswith('json'):
            cleaned = cleaned[4:]
    idx = cleaned.find('{')
    if idx < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(cleaned[idx:])
        return obj if isinstance(obj, dict) else None
    except ValueError:
        return None


def _digest(obj, limit=1500):
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        s = str(obj)
    return s if len(s) <= limit else s[:limit] + '...[truncated]'


class AgentLoop(object):
    """评价 Agent 主循环：自主选工具、预算与停止、轨迹、机械收口。"""

    def __init__(self, owner_root, target_root, run_id, mode='self',
                 contract_path=None, use_llm=False, max_model_calls=10,
                 out_dir=None, now=None, want_html=True, run_dir=None):
        self.owner_root = os.path.abspath(owner_root)
        self.target_root = os.path.abspath(target_root)
        self.run_id = run_id
        self.mode = mode
        self.use_llm = use_llm
        self.now = now or utc_now_iso()
        self.stamp = self.now.replace('-', '').replace(':', '').replace('T', '-').split('.')[0]
        suffix = ''.join(ch for ch in run_id if ch.isdigit())[-6:] or 'na'
        self.eval_id = 'EVAL-%s-%s-%s-%s' % (
            self.stamp, mode, suffix, uuid.uuid4().hex[:4])
        self.out_dir = os.path.abspath(out_dir or os.path.join(self.owner_root,
                                                              'review', 'evaluation'))
        os.makedirs(self.out_dir, exist_ok=True)
        self.out_path = os.path.join(self.out_dir, self.eval_id + '.json')
        self.trace_path = os.path.join(self.out_dir, self.eval_id + '.trace.jsonl')
        self.budget = Budget(max_model_calls=max_model_calls)
        self.verify_claims_result = None
        self.skill, self.rubric = load_skill_and_rubric()
        self.contract, self.contract_note = load_contract(
            self.owner_root, self.target_root, mode, contract_path)
        self.tools = RestrictedTools(self.owner_root, self.target_root, run_id,
                                     self.contract, mode, self.budget,
                                     run_dir=run_dir)
        self.observations = []
        self.suggested_checks = []
        self.not_checked = []
        self.model_mode = 'deterministic'
        self.scores = {}
        self.want_html = want_html

    # ------------------------------------------------------------- 轨迹
    def _trace(self, event, **fields):
        row = {'ts': utc_now_iso(), 'eval_id': self.eval_id,
               'event': event, 'mode': self.mode}
        row.update(fields)
        with open(self.trace_path, 'a', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')

    def _call(self, turn, name, args):
        result = self.tools.dispatch(name, args)
        if (name == 'request_registered_test' and
                (args or {}).get('test_id') == 'verify_claims' and result.get('ok')):
            self.verify_claims_result = result
        self._trace('tool_call', turn=turn, tool=name,
                    args=_digest(args, 600), result=_digest(result))
        return result

    def _known_evidence_ids(self):
        """模型可引用的证据 ID：只取轨迹里真实出现过的路径，不凭空放宽。"""
        known = set()
        if not os.path.isfile(self.trace_path):
            return known
        try:
            with open(self.trace_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    result = row.get('result') or {}
                    if isinstance(result, dict):
                        p = result.get('path')
                        if isinstance(p, str):
                            known.add(p)
                        for it in result.get('items') or []:
                            if isinstance(it, dict) and it.get('path'):
                                known.add(it['path'])
        except OSError:
            pass
        return known

    # ------------------------------------------------------------- 提示
    def _messages(self):
        criteria = [{'id': c['id'], 'criterion': c['criterion'],
                     'expected_evidence': c['expected_evidence']}
                    for c in self.rubric['criteria']]
        scoring = self.rubric.get('evaluation_scoring') or {}
        subcriteria = [{'id': s['id'], 'max': s['max'],
                        'evidence_refs': s.get('evidence_refs', []),
                        'note': s.get('note', '')}
                       for s in scoring.get('subcriteria', [])]
        system = (self.skill + '\n\n## 本次运行的机器判据（rubric 摘要）\n'
                  + json.dumps({
                      'rubric_id': self.rubric['id'],
                      'version': self.rubric['version'],
                      'status': self.rubric['status'],
                      'four_states': self.rubric['evaluation_agent']['four_states'],
                      'budget': self.rubric['evaluation_agent']['budget'],
                      'criteria': criteria,
                      'scoring_framework': scoring.get('framework'),
                      'scoring_subcriteria': subcriteria,
                      'blocking_rules': [r['id'] + ' ' + r['name']
                                         for r in self.rubric['blocking_rules']['rules']],
                  }, ensure_ascii=False))
        user = json.dumps({
            'task': '对目标快照做工程证据审查；自主选择工具，产出最终观察与最小补查建议。',
            'mode': self.mode, 'run_id': self.run_id,
            'target': self.target_root,
            'contract_note': self.contract_note,
            'contract_present': self.contract is not None,
            'model_budget': self.budget.model_calls_max,
            'tool_protocol': ('每轮输出一个 JSON：{"tool": ..., "args": ..., "reason": ...}；'
                              '取证充分后输出 {"final": true, "observations": [...], '
                              '"suggested_checks": [...], "evaluation_scores": [...]}，建议 3—6 轮内收尾。'
                              '最终轮必须简短：observations 最多 3 条、每条不超过 80 字；'
                              '不要把逐项长篇分析写进 observations——那是证据审查区的内容，'
                              '分数写进 evaluation_scores 即可。输出必须是完整合法的 JSON，不要被截断'),
            'score_contract': ('按 rubric.evaluation_scoring.subcriteria 逐子项给评测分：'
                               '{"subcriterion_id","score","max","rationale","evidence_ids","evidence_level"}；'
                               'score 为 0..max 的整数，证据不足给 null 并说明缺什么；'
                               'max 必须与子项定义一致，不得自造子项或改满分；'
                               'rationale 一句人话说明扣分理由，evidence_ids 只引用你真实读到的证据；'
                               'S4 个人能力自述只到 CLAIM_ONLY，须标注为自述，须独立核对；'
                               '评测分不是课程最终成绩、不进判定、'),
        }, ensure_ascii=False)
        return [{'role': 'system', 'content': system},
                {'role': 'user', 'content': user}]

    # ------------------------------------------------------------- 循环
    def _model_phase(self, messages):
        model = describe_model(self.owner_root)
        self._trace('start', eval_id=self.eval_id, target=self.target_root,
                    run_id=self.run_id, contract_note=self.contract_note,
                    model=model.get('model'), use_llm=self.use_llm)
        if not self.use_llm:
            return self._fallback('显式 --no-llm：确定性路径')
        if not model.get('configured'):
            return self._fallback('未配置模型（key.txt 缺失）')

        while self.budget.consume_model():
            turn = self.budget.model_calls
            ok, text = chat(self.owner_root, messages,
                            max_tokens=registry.LLM_MAX_TOKENS)
            self._trace('model_response', turn=turn, ok=ok,
                        raw=_digest({'text': text}, 900))
            if not ok:
                return self._fallback('模型调用失败：%s' % text)
            parsed = _parse_model_output(text)
            if not parsed:
                self._trace('parse_error', turn=turn, raw=_digest({'text': text}, 600))
                # 一次重收：超长 JSON 被 token 截断时，要求只回简短 final 结构。
                # 不自己补全 JSON——那是编造模型输出。
                if self.budget.consume_model():
                    retry_turn = self.budget.model_calls
                    messages.append({'role': 'assistant', 'content': text[:2000]})
                    messages.append({'role': 'user', 'content': json.dumps({
                        'hint': ('上一次输出不是完整 JSON（可能被截断）。'
                                 '请只输出：{"final": true, "observations": [最多3条每条80字], '
                                 '"suggested_checks": [], "evaluation_scores": [...]}。'
                                 '不要长篇分析，不要 Markdown 包裹。')}, ensure_ascii=False)})
                    ok2, text2 = chat(self.owner_root, messages,
                                      max_tokens=registry.LLM_MAX_TOKENS)
                    self._trace('model_response', turn=retry_turn, ok=ok2,
                                raw=_digest({'text': text2}, 900))
                    if ok2:
                        parsed = _parse_model_output(text2)
                if not parsed:
                    self.observations.append('模型输出两次不可解析，已降级确定性收口')
                    break
            if parsed.get('final'):
                self.observations.extend(
                    [str(x) for x in (parsed.get('observations') or [])][:20])
                self.suggested_checks.extend(
                    [str(x) for x in (parsed.get('suggested_checks') or [])][:20])
                scoring = self.rubric.get('evaluation_scoring') or {}
                max_by_id = {s['id']: s['max']
                             for s in scoring.get('subcriteria', [])}
                self.scores = _validate_scores(
                    parsed.get('evaluation_scores') or parsed.get('scores'),
                    max_by_id, self._known_evidence_ids())
                self._trace('final', turn=turn, reason=str(parsed.get('reason') or ''),
                            evaluation_scores={k: v['score']
                                               for k, v in self.scores.items()})
                break
            tool = parsed.get('tool')
            args = parsed.get('args') or {}
            result = self._call(turn, tool, args)
            remaining = self.budget.model_calls_max - self.budget.model_calls
            payload = {'tool_result': result, 'remaining_model_calls': remaining}
            if remaining <= 2:
                payload['hint'] = ('剩余交互不多；证据已足够时下一轮请直接输出 '
                                   '{"final": true, "observations": [...], '
                                   '"suggested_checks": [...]}')
            messages.append({'role': 'assistant', 'content': text})
            messages.append({'role': 'user', 'content': json.dumps(
                payload, ensure_ascii=False, default=str)[:6000]})
        self.model_mode = 'llm'
        return None

    def _fallback(self, reason):
        """降级：仍执行契约核对、证据枚举与机械核对，不把未判读写成通过。"""
        self._trace('start', eval_id=self.eval_id, target=self.target_root,
                    run_id=self.run_id, contract_note=self.contract_note,
                    model=None, use_llm=self.use_llm)
        self._trace('fallback', reason=reason)
        self.observations.append('降级原因：%s；四状态仍由机械核对收口' % reason)
        for i, (name, args) in enumerate((
                ('get_approved_contract', {}),
                ('list_evidence', {}),
                ('request_registered_test',
                 {'test_id': 'verify_claims', 'target_id': self.run_id})), 1):
            self._call('fallback-%d' % i, name, args)
        self.model_mode = 'deterministic'
        return reason

    # ------------------------------------------------------------- 收口
    def _mechanical_verdict(self):
        findings, report, records = precheck(self.tools.run_dir)
        snapshot_status, snapshot_reason = _decide(findings, report)
        blocking = [f for f in findings if f['level'] == 'FAIL']
        report_version = (report or {}).get('versions', {}).get('rule_pack')
        contract_version = (self.contract or {}).get('rule_pack_version')
        version_mismatch = bool(report_version and contract_version
                                and report_version != contract_version)
        # 机械核对是收口的前提，不能依赖模型是否想起调 verify_claims：
        # 模型模式下若没调该工具，过去会让 mechanically_checked=False，
        # 导致字段全符合也被判 INSUFFICIENT。这里直接跑 precheck 收口。
        mechanically_checked = not any(f['level'] == 'FAIL' for f in findings)

        # T-M5-12 字段级内容核对：读真实字段，三态（match/mismatch/missing）。
        # 只读、走 RestrictedTools 白名单；只加严不放宽——字段未全符合时
        # content_checked 强制为 False，任何一项都不得仅凭"文件在"判 PASS。
        field_result = field_check_all(load_field_spec(), self.tools, self.run_id)
        self.field_check_result = field_result
        field_by_id = {c['criterion_id']: c for c in field_result['criteria']}
        self._trace('field_check', run_id=self.run_id,
                    criteria=[{'criterion_id': c['criterion_id'],
                               'fields': [{'id': f['id'],
                                           'path': f.get('path_expanded'),
                                           'kind': f['kind'],
                                           'status': f['status']}
                                          for f in c['fields']],
                               'summary': c['summary']}
                              for c in field_result['criteria']])

        items = []
        for crit in self.rubric['criteria']:
            expected = [p.replace('evidence/RUN-*/', 'evidence/%s/' % self.run_id)
                        for p in crit['expected_evidence']]
            listing = self.tools.list_evidence(expected)
            missing = [it['path'] for it in listing['items'] if not it['exists']]
            rejected = [it['path'] for it in listing['items'] if not it.get('allowed', True)]
            evidence_ids = [it['path'] for it in listing['items'] if it['exists']]

            # T-M5-12：字段级核对是 PASS 的必要条件（加严）。字段全符合才算
            # 内容级核过；任一字段 mismatch/missing 都不得判 PASS。
            fc = field_by_id.get(crit['id'], {})
            fs = fc.get('summary', {})
            field_ok = bool(fs.get('all_match'))
            field_bad = [f['id'] for f in fc.get('fields', [])
                         if f['status'] != 'match']

            # 机械层能核到的最深程度：引用/版本/结构由 verify_claims 统一核对，
            # 叠加字段级内容核对。原先只给 E-05 开口，导致上层 any(INSUFFICIENT)
            # 恒真、PASS 永不可达，与总档 A-08「四状态」不符。
            content_checked = bool(mechanically_checked
                                   and snapshot_status == 'PASS'
                                   and not missing and not rejected
                                   and field_ok)
            if self.contract is None and self.mode == 'peer':
                status, finding = ('INSUFFICIENT_EVIDENCE',
                                   '互评缺少目标批准契约，本项未做实质审查')
                missing.append('evaluation/contract.json（目标仓库）')
            elif crit['id'] == 'E-05' and blocking:
                status = 'FAIL'
                finding = ('确定性预检命中 %d 项阻断问题：%s'
                           % (len(blocking), '；'.join(f['code'] for f in blocking[:3])))
            elif missing or rejected:
                status = 'INSUFFICIENT_EVIDENCE'
                finding = '证据缺口：%s' % ', '.join((missing + rejected)[:3])
            elif version_mismatch:
                status = 'INSUFFICIENT_EVIDENCE'
                finding = ('报告规则包 %s 与契约 %s 不一致；旧证据不判新版本'
                           % (report_version, contract_version))
            elif content_checked:
                status = 'PASS'
                finding = ('引用、版本、结构经 verify_claims 机械核对通过，'
                           '字段级核对全部符合；范围仅限机械/字段层，'
                           '结论语义正确性仍待人工复核')
            else:
                status = 'INSUFFICIENT_EVIDENCE'
                if field_bad and not (missing or rejected):
                    finding = ('字段级核对未全符合（%s）；仅存在性不足以判定内容合格'
                               % ', '.join(field_bad[:6]))
                else:
                    finding = '锚点或字段存在缺口；仅存在性不足以判定内容合格'
            chain_steps = []
            for f in fc.get('fields', []):
                chain_steps.append({
                    'step_id': f['id'],
                    'question': f.get('note') or '字段核对',
                    'path': f.get('path_expanded') or f.get('path'),
                    'method': f['kind'],
                    'expectation': '见字段规范',
                    'observed': f['observed'],
                    'status': f['status'],
                    'status_text': {'match': '符合', 'mismatch': '不符合',
                                    'missing': '读不到'}.get(f['status'], f['status']),
                })
            items.append({
                'criterion_id': crit['id'],
                'criterion': crit['criterion'],
                'plain': crit.get('plain') or crit['criterion'],
                'weight_ref': crit['weight_ref'],
                'status': status,
                'evidence_level': 'STATIC',
                'content_checked': content_checked,
                'field_check': {
                    'summary': fs,
                    'fields': [{'id': f['id'], 'path': f.get('path_expanded'),
                                'kind': f['kind'], 'status': f['status'],
                                'observed': f['observed']}
                               for f in fc.get('fields', [])],
                },
                'evidence_chain': {'criterion_id': crit['id'], 'steps': chain_steps},
                'evidence_ids': evidence_ids[:12],
                'finding': finding,
                'scope': '目标 %s 的 %s（%s）' % (self.mode, self.run_id,
                                                self.target_root),
                'missing_evidence': missing[:8] + field_bad[:8],
                'suggested_check': ('补齐上述证据/字段后复跑；'
                                    '内容正确性需人工抽验' if status != 'PASS'
                                    else '人工抽验 2—3 个关键 Claim'),
                # E 项是证据审查项，不是评分项；评测分独立在顶层 evaluation_scores，
                # 按 S1—S4 子项给，不塞进 E 项，避免把审查项误当评分项。
                'score_suggestion': None,
            })

        if blocking or snapshot_status == 'FAIL':
            top = 'FAIL'
        elif (self.contract is None and self.mode == 'peer') or version_mismatch:
            top = 'INSUFFICIENT_EVIDENCE'
        elif any(i['status'] == 'INSUFFICIENT_EVIDENCE' for i in items):
            top = 'INSUFFICIENT_EVIDENCE'
        elif snapshot_status == 'INSUFFICIENT_EVIDENCE':
            top = 'INSUFFICIENT_EVIDENCE'
        else:
            top = 'PASS'
        self.version_check = {
            'report_rule_pack': report_version,
            'contract_rule_pack': contract_version,
            'mismatch': version_mismatch,
            'suggested_check': ('按当前规则包生成新 RUN 正本，或提供版本豁免记录；'
                                '历史正本不改写' if version_mismatch else None),
        }
        self.coverage_note = (
            '机械层完成 %d 项锚点核对，其中 %d 项做了引用级机械核对；'
            '字段级内容核对与版本对齐待补，结论不作为内容通过证明'
            % (len(items), sum(1 for i in items if i['content_checked'])))
        # 判定指纹只含机械结果：状态、字段三态、版本核对。不含模型建议分、
        # observations、时间、eval_id —— 同快照重跑必须逐字节一致。
        from .checker import verdict_digest
        digest_payload = {
            'run_id': self.run_id,
            'status': top,
            'snapshot_status': snapshot_status,
            'version_check': {'mismatch': version_mismatch},
            'criteria': [{'criterion_id': i['criterion_id'], 'status': i['status'],
                          'fields': [{'id': f['id'], 'status': f['status']}
                                     for f in i['field_check']['fields']]}
                         for i in items],
        }
        self.verdict_digest = verdict_digest(digest_payload)
        return top, snapshot_status, snapshot_reason, items, findings, records

    def run(self):
        # 默认纯 harness：不调 API。分项评测分由 scoring.py 按字段三态机械算出，
        # 覆盖全部子项，不靠模型自主取证（模型受预算限制会漏读证据）。
        if self.use_llm:
            messages = self._messages()
            self._model_phase(messages)
        else:
            self._trace('scoring', mode='deterministic',
                        note='证据包由 scoring.py 生成，分数待 harness 依证据满足度主观给出')
        (top, snapshot_status, snapshot_reason,
         items, findings, records) = self._mechanical_verdict()

        # 证据包与是否调模型无关：两种模式都要生成，供 next_action 与 harness 评分。
        from .scoring import build_from_project
        self.evidence_pack = build_from_project(
            self.target_root,
            context={'run_id': self.run_id, 'target': self.target_root},
            rubric=self.rubric)
        self._trace('evidence_pack_ready',
                    subcriteria=len(self.evidence_pack['subcriteria']))
        if not self.use_llm:
            # 分数待 harness 看过证据包后主观给出；此处不猜分。
            self.scoring = None
            self.scores = {}

        if self.budget.exhausted_notes:
            self.observations.append(
                '预算：%s；模型主动取数停止，全部审查项已由确定性机械核对收口'
                % '；'.join(self.budget.exhausted_notes))
        if getattr(self, 'version_check', {}).get('mismatch'):
            self.not_checked.append(self.version_check['suggested_check'])
        unchecked = [i['criterion_id'] for i in items
                     if not i.get('content_checked')]
        if unchecked:
            self.not_checked.append('字段/锚点核对未全符合：%s' % ', '.join(unchecked))
        result = {
            'eval_id': self.eval_id,
            'generated_at': self.now,
            'target': self.target_root,
            'owner': self.owner_root,
            'mode': self.mode,
            'run_id': self.run_id,
            'status': top,
            'reason': snapshot_reason,
            'snapshot_status': snapshot_status,
            'versions': {
                'rule_pack': (self.contract or {}).get('rule_pack_version',
                                                       registry.RULE_PACK_VERSION),
                'rubric': self.rubric['version'],
                'rubric_status': self.rubric['status'],
                'skill': 'v1.3',
            },
            'contract': {'present': self.contract is not None,
                         'note': self.contract_note,
                         'approved_by': (self.contract or {}).get('approved_by')},
            'version_check': getattr(self, 'version_check', {}),
            'field_check': getattr(self, 'field_check_result', None),
            'coverage_note': getattr(self, 'coverage_note', ''),
            'model': {'mode': self.model_mode,
                      'name': (None if not self.use_llm
                               else describe_model(self.owner_root).get('model')),
                      'note': ('纯 harness：不调用 API，只摆证据；评测分由调用方看过证据后给出；'
                               '分数不参与四状态判定，不进判定指纹'
                               if not self.use_llm else
                               '模型输出只进 observations 与分项评测分；不参与四状态判定')},
            'verdict_digest': getattr(self, 'verdict_digest', None),
            'evaluation_scores': (getattr(self, 'scoring', None)
                                  or [self.scores[s['id']]
                                      for s in (self.rubric.get('evaluation_scoring') or {})
                                      .get('subcriteria', []) if s['id'] in self.scores]),
            'scoring_status': ('pending_harness' if not getattr(self, 'scoring', None)
                               else 'scored'),
            'evidence_pack': getattr(self, 'evidence_pack', None),
            'scoring_framework': (self.rubric.get('evaluation_scoring') or {}).get('framework'),
            'score_contract': ('harness 依证据满足度主观评分；非课程最终成绩'),
            'budget': self.budget.as_dict(),
            'trace_path': self.trace_path,
            'findings': items,
            'precheck_findings': findings,
            'evidence_records_reviewed': len(records),
            'observations': self.observations[:20],
            'suggested_checks': self.suggested_checks[:20],
            'not_checked': self.not_checked,
            'blocking_rules_checked': 'static_only（8 条红线由人工复核，未自动判定）',
            'score_suggestion': None,
        }
        # 评价器自己声明下一步：调用方读 next_action 就知道怎么评分，
        # 不依赖外部文档预先写死流程。模板文件随评价一起产出。
        if result['scoring_status'] == 'pending_harness':
            template_path = os.path.join(
                self.out_dir,
                os.path.splitext(os.path.basename(self.out_path))[0]
                + '.scores.template.json')
            template = {
                sid: {'score': None, 'rationale': '', 'evidence_ids': [],
                      'evidence_level': 'STATIC'}
                for sid in [s['subcriterion_id']
                            for s in (self.evidence_pack or {}).get('subcriteria', [])]
            }
            with open(template_path, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(template, f, ensure_ascii=False, indent=2)
            result['next_action'] = {
                'step': 'score_and_submit',
                'why': ('证据包已就绪、分数未给。请逐项阅读 evidence_pack 中的原文片段，'
                        '按证据对该项的满足程度主观打分，并写扣分理由与证据引用。'),
                'template_path': template_path,
                # 提交接口用语义描述，不写具体命令——换 harness 也能实现。
                'submit': {
                    'target': self.out_path,
                    'source': '<填好的 template_path>',
                    'operation': '把 source 的逐项分数回填到 target，并重渲染其 HTML',
                    'contract': ('source 的键为子项 ID，值为 score/rationale/'
                                 'evidence_ids/evidence_level；target 同路径的 HTML 随之更新'),
                },
                'schema': {'score': '0..max 的整数或 null（证据不足）',
                           'rationale': '扣分理由，须指到具体缺口',
                           'evidence_ids': '引用的证据路径',
                           'evidence_level': 'STATIC / OBSERVED / CLAIM_ONLY'},
            }
        else:
            result['next_action'] = None
        result['scores_template_path'] = (
            result.get('next_action') or {}).get('template_path')
        self._trace('verdict', status=top, snapshot_status=snapshot_status,
                    criteria=len(items),
                    counts={s: sum(1 for i in items if i['status'] == s)
                            for s in VALID_STATUS})
        # HTML 报告：判定区与建议分区分离；模型文本不进判定区、不进指纹。
        # 生成失败不掩盖评价结果，如实记一条 observation。
        html_path = os.path.join(self.out_dir, self.eval_id + '.html')
        if getattr(self, 'want_html', True):
            try:
                write_html(result, self.rubric, html_path)
                result['html_path'] = html_path
            except (OSError, ValueError, TypeError) as e:
                self.observations.append('HTML 生成失败：%s' % e)
                result['html_path'] = None
        with open(self.out_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        lines = ['评价 Agent 输出 · %s' % self.eval_id,
                 '- 目标：%s（%s）｜ RUN：%s' % (self.target_root, self.mode, self.run_id),
                 '- 状态：**%s**（%s）' % (top, snapshot_reason),
                 '- 模式：%s ｜ 模型交互 %d/%d ｜ 注册补测 %d/%d'
                 % (self.model_mode, self.budget.model_calls,
                    self.budget.model_calls_max, self.budget.tests_used,
                    self.budget.tests_max),
                 '- 审查项：%d 项（%s）'
                 % (len(items), '、'.join('%s %d' % (s, sum(1 for i in items
                                                          if i['status'] == s))
                                       for s in VALID_STATUS
                                       if any(i['status'] == s for i in items))),
                 '- 契约：%s' % self.contract_note,
                 '- 判定指纹：%s（同快照重跑应一致）'
                 % (getattr(self, 'verdict_digest', None) or '未生成')[:16],
                 '- 轨迹：%s' % self.trace_path,
                 '- HTML：%s' % (result.get('html_path') or '未生成')]
        if self.not_checked:
            lines.append('- 未完成项：%s' % '；'.join(self.not_checked[:3]))
        result['text'] = '\n'.join(lines)
        result['out_path'] = self.out_path
        return result


def run_agent(owner_root, target_root, run_id, mode='self', contract_path=None,
              use_llm=False, max_model_calls=10, out_dir=None, want_html=True,
              run_dir=None):
    return AgentLoop(owner_root, target_root, run_id, mode=mode,
                     contract_path=contract_path, use_llm=use_llm,
                     max_model_calls=max_model_calls, out_dir=out_dir,
                     want_html=want_html, run_dir=run_dir).run()


def apply_scores(eval_path, scores_path):
    """把 harness 看过证据后给的分回填到评价 JSON，重渲染 HTML。

    scores 文件格式：{"S1.需求": {"score": 5, "rationale": "...",
                                  "evidence_ids": [...], "evidence_level": "STATIC"}, ...}
    只接受已知子项、0..max 整数或 null；越界/未知项丢弃，不编造。
    """
    with open(eval_path, 'r', encoding='utf-8') as f:
        result = json.load(f)
    with open(scores_path, 'r', encoding='utf-8') as f:
        submitted = json.load(f)
    pack = result.get('evidence_pack')
    if not pack:
        return {'ok': False, 'error': '该评价没有证据包，无法回填评分'}
    from .scoring import validate_scores
    scored = validate_scores(submitted, pack)
    result['evaluation_scores'] = scored
    result['scoring_status'] = 'scored'
    result['scoring_source'] = 'harness_subjective（依据证据满足度）'
    with open(eval_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    html_path = os.path.join(os.path.dirname(os.path.abspath(eval_path)),
                             os.path.splitext(os.path.basename(eval_path))[0] + '.html')
    skill, rubric = load_skill_and_rubric()
    write_html(result, rubric, html_path)
    return {'ok': True, 'eval_path': eval_path, 'html_path': html_path,
            'scored': len(scored),
            'total': sum(s['score'] for s in scored if isinstance(s['score'], int))}
