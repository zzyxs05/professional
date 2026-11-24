# -*- coding: utf-8 -*-
"""agent.py · 评价 Agent：多轮工具编排 + 确定性收口 + 轨迹留痕

链条（总档 §2.6）：Agent 审查 → 学生签署 → 教师复评，最终成绩只在教师层。
判定契约：模型自主选择审查项与受限工具，四状态由机械核对结果收口；
模型输出只进入 observations / suggested_checks，不升级结论、不产生分数。
"""

import json
import os
import uuid

from core import registry
from core.evidence import check_run_id, utc_now_iso
from .contract import load_contract
from .llm import chat, describe_model
from .precheck import precheck
from .tools import RestrictedTools

SKILL_DIR = os.path.join(os.path.dirname(__file__), 'skills', 'evidence-review')
VALID_STATUS = ('PASS', 'FAIL', 'INSUFFICIENT_EVIDENCE', 'NOT_APPLICABLE')


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
    """兼容旧接口的确定性快路径；正式评价请走 run_agent / cli.py evaluate。"""
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
             '- findings：%d 项' % len(findings),
             '- 签署栏：本组（　　）｜对抗组（　　）｜教师（　　）']
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
                 contract_path=None, use_llm=True, max_model_calls=10,
                 out_dir=None, now=None):
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
                                     self.contract, mode, self.budget)
        self.observations = []
        self.suggested_checks = []
        self.not_checked = []
        self.model_mode = 'deterministic'

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

    # ------------------------------------------------------------- 提示
    def _messages(self):
        criteria = [{'id': c['id'], 'criterion': c['criterion'],
                     'expected_evidence': c['expected_evidence']}
                    for c in self.rubric['criteria']]
        system = (self.skill + '\n\n## 本次运行的机器判据（rubric 摘要）\n'
                  + json.dumps({
                      'rubric_id': self.rubric['id'],
                      'version': self.rubric['version'],
                      'status': self.rubric['status'],
                      'four_states': self.rubric['evaluation_agent']['four_states'],
                      'budget': self.rubric['evaluation_agent']['budget'],
                      'criteria': criteria,
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
                              '"suggested_checks": [...]}，建议 3—6 轮内收尾'),
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
                self.observations.append('模型输出不可解析，已降级确定性收口')
                self._trace('parse_error', turn=turn, raw=_digest({'text': text}, 600))
                break
            if parsed.get('final'):
                self.observations.extend(
                    [str(x) for x in (parsed.get('observations') or [])][:20])
                self.suggested_checks.extend(
                    [str(x) for x in (parsed.get('suggested_checks') or [])][:20])
                self._trace('final', turn=turn, reason=str(parsed.get('reason') or ''))
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
        vc = self.verify_claims_result or {}
        mechanically_checked = bool(vc.get('ok') and not vc.get('findings'))

        items = []
        for crit in self.rubric['criteria']:
            expected = [p.replace('evidence/RUN-*/', 'evidence/%s/' % self.run_id)
                        for p in crit['expected_evidence']]
            listing = self.tools.list_evidence(expected)
            missing = [it['path'] for it in listing['items'] if not it['exists']]
            rejected = [it['path'] for it in listing['items'] if not it.get('allowed', True)]
            evidence_ids = [it['path'] for it in listing['items'] if it['exists']]

            # 机械层能核到的最深程度：引用/版本/结构由 verify_claims 统一核对。
            # 一旦快照通过且该项锚点齐全，即可判「通过（仅机械层）」——
            # 原先只给 E-05 开口，导致上层 any(INSUFFICIENT) 恒真、PASS 永不可达，
            # 与总档 A-08「四状态」不符。
            content_checked = bool(mechanically_checked
                                   and snapshot_status == 'PASS'
                                   and not missing and not rejected)
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
                finding = ('引用、版本、结构经 verify_claims 机械核对通过；'
                           '范围仅限机械层，结论语义正确性仍待人工复核')
            else:
                status = 'INSUFFICIENT_EVIDENCE'
                finding = '锚点齐全但未做字段级内容核对；仅存在性不足以判定内容合格'
            items.append({
                'criterion_id': crit['id'],
                'criterion': crit['criterion'],
                'weight_ref': crit['weight_ref'],
                'status': status,
                'evidence_level': 'STATIC',
                'content_checked': content_checked,
                'evidence_ids': evidence_ids[:12],
                'finding': finding,
                'scope': '目标 %s 的 %s（%s）' % (self.mode, self.run_id,
                                                self.target_root),
                'missing_evidence': missing[:8],
                'suggested_check': ('补齐上述证据后复跑；'
                                    '内容正确性需人工抽验' if status != 'PASS'
                                    else '人工抽验 2—3 个关键 Claim'),
                'score_suggestion': None,
                'human_signoff': 'pending',
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
        return top, snapshot_status, snapshot_reason, items, findings, records

    def run(self):
        messages = self._messages()
        self._model_phase(messages)
        (top, snapshot_status, snapshot_reason,
         items, findings, records) = self._mechanical_verdict()

        if self.budget.exhausted_notes:
            self.observations.append(
                '预算：%s；模型主动取数停止，全部审查项已由确定性机械核对收口'
                % '；'.join(self.budget.exhausted_notes))
        if getattr(self, 'version_check', {}).get('mismatch'):
            self.not_checked.append(self.version_check['suggested_check'])
        unchecked = [i['criterion_id'] for i in items
                     if not i.get('content_checked')]
        if unchecked:
            self.not_checked.append('未做字段级内容核对：%s' % ', '.join(unchecked))
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
                'skill': 'v1.0',
            },
            'contract': {'present': self.contract is not None,
                         'note': self.contract_note,
                         'approved_by': (self.contract or {}).get('approved_by')},
            'version_check': getattr(self, 'version_check', {}),
            'coverage_note': getattr(self, 'coverage_note', ''),
            'model': {'mode': self.model_mode,
                      'name': describe_model(self.owner_root).get('model'),
                      'note': '模型输出只进 observations，不参与四状态判定'},
            'budget': self.budget.as_dict(),
            'trace_path': self.trace_path,
            'findings': items,
            'precheck_findings': findings,
            'evidence_records_reviewed': len(records),
            'observations': self.observations[:20],
            'suggested_checks': self.suggested_checks[:20],
            'not_checked': self.not_checked,
            'blocking_rules_checked': 'static_only（8 条红线由人工复核，未自动判定）',
            'signoff_chain': {
                'self_review': '本组人工签署（pending）',
                'peer_response': '对方回应（待发生）' if self.mode == 'peer' else '不适用',
                'teacher_review': '教师复评（最终成绩只在教师层）',
            },
            'score_suggestion': None,
            'human_signoff': 'pending',
        }
        self._trace('verdict', status=top, snapshot_status=snapshot_status,
                    criteria=len(items),
                    counts={s: sum(1 for i in items if i['status'] == s)
                            for s in VALID_STATUS})
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
                 '- 轨迹：%s' % self.trace_path,
                 '- 签署：本组（pending）｜对方回应｜教师复评']
        if self.not_checked:
            lines.append('- 未完成项：%s' % '；'.join(self.not_checked[:3]))
        result['text'] = '\n'.join(lines)
        result['out_path'] = self.out_path
        return result


def run_agent(owner_root, target_root, run_id, mode='self', contract_path=None,
              use_llm=True, max_model_calls=10, out_dir=None):
    return AgentLoop(owner_root, target_root, run_id, mode=mode,
                     contract_path=contract_path, use_llm=use_llm,
                     max_model_calls=max_model_calls, out_dir=out_dir).run()
