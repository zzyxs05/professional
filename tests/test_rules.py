# -*- coding: utf-8 -*-
"""test_rules.py · 规则逻辑测试（合成 smali / 合成事实，不依赖真实 APK）"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import registry
from core.adapters import SmaliFacts
from core.rules.code import r_code_01, r_code_02
from core.rules.common import (effective_ops, is_const_true_return,
                               is_empty_array_return, is_empty_method_body,
                               origin_line)
from core.rules.net import r_net_01, r_net_02
from core.rules.perm import r_perm_01


class FakeCtx(object):
    def __init__(self, smali=None, manifest=None, package='com.test.app', dex=None, res=None):
        self.smali = smali
        self.manifest = manifest
        self.app_package = package
        self.dex = dex
        self.res = res
        self.rule_notes = []


def make_smali_tree(files):
    """files: {'smali/com/test/app/A.smali': 内容} → SmaliFacts"""
    root = tempfile.mkdtemp(prefix='apkaudit_smali_')
    for rel, content in files.items():
        p = os.path.join(root, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
    return root, SmaliFacts(root)


SMALI_HEAD = '.class public Lcom/test/app/{0};\n.super Ljava/lang/Object;\n.source "{0}.java"\n\n'


class TestCommonOps(unittest.TestCase):
    def test_effective_ops_filters(self):
        body = [
            (10, '    .locals 2'),
            (11, '    .annotation system Ldalvik/annotation/Throws;'),
            (12, '        value = { Ljava/lang/Exception; }'),
            (13, '    .end annotation'),
            (14, '    .line 5'),
            (15, '    :try_start_0'),
            (16, '    invoke-virtual {p0}, Lcom/test/app/A;->x()V'),
            (17, ''),
            (18, '    return-void'),
        ]
        ops = effective_ops(body)
        insns = [op for _, op in ops]
        self.assertEqual(insns, ['invoke-virtual {p0}, Lcom/test/app/A;->x()V', 'return-void'])

    def test_empty_method_body(self):
        ops = effective_ops([(1, '    .locals 0'), (2, '    return-void')])
        self.assertTrue(is_empty_method_body(ops))
        ops2 = effective_ops([(1, '    invoke-virtual {p0}, Lx;->y()V'), (2, '    return-void')])
        self.assertFalse(is_empty_method_body(ops2))

    def test_const_true_return(self):
        ops = effective_ops([(1, '    const/4 p0, 0x1'), (2, '    return p0')])
        self.assertTrue(is_const_true_return(ops))
        ops2 = effective_ops([
            (1, '    invoke-static {}, Ljavax/net/ssl/HttpsURLConnection;->getDefaultHostnameVerifier()Ljavax/net/ssl/HostnameVerifier;'),
            (2, '    move-result-object p0'),
            (3, '    return p0')])
        self.assertFalse(is_const_true_return(ops2))

    def test_empty_array_return(self):
        ops = effective_ops([
            (1, '    .locals 0'),
            (2, '    const/4 p0, 0x0'),
            (3, '    new-array p0, p0, [Ljava/security/cert/X509Certificate;'),
            (4, '    return-object p0')])
        self.assertTrue(is_empty_array_return(ops))

    def test_origin_line(self):
        lines = ['# comment', '.method x()V', '    .line 42', '    return-void', '.end method']
        self.assertEqual(origin_line(lines, 4), 42)


class TestPermRules(unittest.TestCase):
    def test_perm01_combo_hit(self):
        src = (SMALI_HEAD.format('App') +
               '.method public run()V\n    .locals 2\n'
               '    .line 10\n'
               '    invoke-virtual {p0, v0}, Landroid/app/AlarmManager;->setRepeating(IJJLandroid/app/PendingIntent;)V\n'
               '    .line 11\n'
               '    new-instance v0, Landroid/media/MediaRecorder;\n'
               '    invoke-direct {v0}, Landroid/media/MediaRecorder;-><init>()V\n'
               '    return-void\n.end method\n')
        root, smali = make_smali_tree({'smali/com/test/app/App.smali': src})
        try:
            hits = r_perm_01.run(FakeCtx(smali=smali))
            self.assertGreater(len(hits), 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_perm01_single_side_silent(self):
        src = (SMALI_HEAD.format('App') +
               '.method public run()V\n    .locals 2\n'
               '    invoke-virtual {p0, v0, v1, v2}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z\n'
               '    return-void\n.end method\n')
        root, smali = make_smali_tree({'smali/com/test/app/App.smali': src})
        try:
            hits = r_perm_01.run(FakeCtx(smali=smali))
            self.assertEqual(hits, [])   # 仅调度侧 → 组合不成立（good01 口径）
        finally:
            shutil.rmtree(root, ignore_errors=True)


    def test_perm01_chain_upgrades(self):
        # 调度 → 目标组件(const-class) → 目标内含敏感 API = 调用链证据 → 已确认档
        main = ('.class public Lcom/test/app/Main;\n.super Landroid/app/Activity;\n\n'
                '.method private schedule()V\n    .locals 4\n'
                '    const-class v2, Lcom/test/app/Svc;\n'
                '    new-instance v0, Landroid/content/Intent;\n'
                '    invoke-direct {v0, p0, v2}, Landroid/content/Intent;-><init>(Landroid/content/Context;Ljava/lang/Class;)V\n'
                '    invoke-static {p0, v2, v0, v3}, Landroid/app/PendingIntent;->getService(Landroid/content/Context;ILandroid/content/Intent;I)Landroid/app/PendingIntent;\n'
                '    invoke-virtual {v1, v4, v5, v6}, Landroid/app/AlarmManager;->setRepeating(IJJLandroid/app/PendingIntent;)V\n'
                '    return-void\n.end method\n')
        svc = ('.class public Lcom/test/app/Svc;\n.super Landroid/app/Service;\n\n'
               '.method onStart()V\n    .locals 1\n'
               '    new-instance v0, Landroid/media/MediaRecorder;\n'
               '    invoke-direct {v0}, Landroid/media/MediaRecorder;-><init>()V\n'
               '    return-void\n.end method\n')
        root, smali = make_smali_tree({'smali/com/test/app/Main.smali': main,
                                       'smali/com/test/app/Svc.smali': svc})
        try:
            hits = r_perm_01.run(FakeCtx(smali=smali))
            self.assertGreaterEqual(len(hits), 3)
            self.assertTrue(all(h.max_status is None for h in hits))  # 继承规则上限=已确认
            self.assertTrue(any('调度目标组件' in (h.note or '') for h in hits))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_perm01_coexistence_stays_review(self):
        # 有调度 + 有敏感 API，但无可解析调度目标 → 回退疑点组合档（待复核）
        src = (SMALI_HEAD.format('App') +
               '.method public run()V\n    .locals 2\n'
               '    invoke-virtual {p0, v0}, Landroid/app/AlarmManager;->setRepeating(IJJLandroid/app/PendingIntent;)V\n'
               '    new-instance v1, Landroid/media/MediaRecorder;\n'
               '    invoke-direct {v1}, Landroid/media/MediaRecorder;-><init>()V\n'
               '    return-void\n.end method\n')
        root, smali = make_smali_tree({'smali/com/test/app/App.smali': src})
        try:
            hits = r_perm_01.run(FakeCtx(smali=smali))
            self.assertGreater(len(hits), 0)
            self.assertTrue(all(h.max_status == registry.STATUS_REVIEW for h in hits))
        finally:
            shutil.rmtree(root, ignore_errors=True)


class TestCodeRules(unittest.TestCase):
    def test_code01_hit(self):
        src = (SMALI_HEAD.format('App') +
               '.method load()V\n    .locals 2\n'
               '    new-instance v0, Ldalvik/system/DexClassLoader;\n'
               '    invoke-direct {v0, p0, p1, p2, p3}, Ldalvik/system/DexClassLoader;-><init>(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/ClassLoader;)V\n'
               '    return-void\n.end method\n')
        root, smali = make_smali_tree({'smali/com/test/app/App.smali': src})
        try:
            hits = r_code_01.run(FakeCtx(smali=smali))
            self.assertGreater(len(hits), 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_code02_requires_three_elements(self):
        two = (SMALI_HEAD.format('App') +
               '.method w()V\n    .locals 2\n'
               '    invoke-virtual {v0, v1}, Landroid/webkit/WebSettings;->setJavaScriptEnabled(Z)V\n'
               '    return-void\n.end method\n')
        three = (SMALI_HEAD.format('App') +
                 '.method w()V\n    .locals 2\n'
                 '    invoke-virtual {v0, v1}, Landroid/webkit/WebSettings;->setJavaScriptEnabled(Z)V\n'
                 '    invoke-virtual {v0, v1}, Landroid/webkit/WebSettings;->setAllowFileAccess(Z)V\n'
                 '    invoke-virtual {p0, v0, v1}, Landroid/webkit/WebView;->addJavascriptInterface(Ljava/lang/Object;Ljava/lang/String;)V\n'
                 '    return-void\n.end method\n')
        root1, s1 = make_smali_tree({'smali/com/test/app/App.smali': two})
        root2, s2 = make_smali_tree({'smali/com/test/app/App.smali': three})
        try:
            self.assertEqual(r_code_02.run(FakeCtx(smali=s1)), [])
            self.assertGreater(len(r_code_02.run(FakeCtx(smali=s2))), 0)
        finally:
            shutil.rmtree(root1, ignore_errors=True)
            shutil.rmtree(root2, ignore_errors=True)


class TestNetRules(unittest.TestCase):
    def test_net01_empty_trustmanager_hit(self):
        src = ('.class Lcom/test/app/TM$1;\n.super Ljava/lang/Object;\n'
               '.implements Ljavax/net/ssl/X509TrustManager;\n\n'
               '.method public checkServerTrusted([Ljava/security/cert/X509Certificate;Ljava/lang/String;)V\n'
               '    .locals 0\n\n    return-void\n.end method\n')
        root, smali = make_smali_tree({'smali/com/test/app/TM$1.smali': src})
        try:
            hits = r_net_01.run(FakeCtx(smali=smali))
            self.assertEqual(len(hits), 1)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_net01_delegating_silent(self):
        src = ('.class Lcom/test/app/TM;\n.super Ljava/lang/Object;\n'
               '.implements Ljavax/net/ssl/X509TrustManager;\n\n'
               '.method public checkServerTrusted([Ljava/security/cert/X509Certificate;Ljava/lang/String;)V\n'
               '    .locals 0\n'
               '    invoke-interface {p0, p1, p2}, Ljavax/net/ssl/X509TrustManager;->checkServerTrusted([Ljava/security/cert/X509Certificate;Ljava/lang/String;)V\n'
               '    return-void\n.end method\n')
        root, smali = make_smali_tree({'smali/com/test/app/TM.smali': src})
        try:
            self.assertEqual(r_net_01.run(FakeCtx(smali=smali)), [])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_net02_proceed_vs_cancel(self):
        proceed = ('.class public Lcom/test/app/WC;\n.super Landroid/webkit/WebViewClient;\n\n'
                   '.method public onReceivedSslError(Landroid/webkit/WebView;Landroid/webkit/SslErrorHandler;Landroid/net/http/SslError;)V\n'
                   '    .locals 0\n'
                   '    invoke-virtual {p2}, Landroid/webkit/SslErrorHandler;->proceed()V\n'
                   '    return-void\n.end method\n')
        cancel = proceed.replace('proceed()V', 'cancel()V')
        root1, s1 = make_smali_tree({'smali/com/test/app/WC.smali': proceed})
        root2, s2 = make_smali_tree({'smali/com/test/app/WC.smali': cancel})
        try:
            self.assertEqual(len(r_net_02.run(FakeCtx(smali=s1))), 1)
            self.assertEqual(r_net_02.run(FakeCtx(smali=s2)), [])
        finally:
            shutil.rmtree(root1, ignore_errors=True)
            shutil.rmtree(root2, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
