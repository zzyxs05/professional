# -*- coding: utf-8 -*-
"""registry.py · 规则与常量唯一来源

- 规则表、阈值、正则、清单全部登记于此；变更 = bump RULE_PACK_VERSION + 记 docs/changes.md。
- 本文件是 specification.md §2 的机器可读实现；两者冲突时以 specification.md 为准并回改本文件。
"""

RULE_PACK_VERSION = "0.1.3"   # 0.1.3：R-PERM-03 静态排除力分档 + 声明即生效排除集 + 权限清单扩至 Android 13+ + 自有代码范围兜底
PROJECT_NAME = "apkaudit"

# ---------------------------------------------------------------- 结论档位
STATUS_CONFIRMED = "已确认"
STATUS_REVIEW = "待复核"
STATUS_UNDECIDED = "无法判定"
STATUS_ORDER = {STATUS_CONFIRMED: 2, STATUS_REVIEW: 1, STATUS_UNDECIDED: 0}

# ---------------------------------------------------------------- 规则元数据
# data_source: manifest / dex_strings / smali_src / res_decoded（可组合）
# max_status: 无 B 通道复核时允许输出的最高档位（融合层不得越过）
# fp_notes: 误报口径（什么不算）——B1 复核的判定标准（b1-v0.2 起注入提示词）
RULE_META = {
    "R-MAN-01": {"name": "导出组件无权限保护", "category": "M", "data_source": ["manifest"], "max_status": STATUS_CONFIRMED, "priority": "P0",
                 "fp_notes": "带组件级 permission/readPermission/writePermission 保护的导出组件不算"},
    "R-MAN-02": {"name": "危险权限声明", "category": "M", "data_source": ["manifest"], "max_status": STATUS_CONFIRMED, "priority": "P0",
                 "fp_notes": "仅 INTERNET 等非敏感权限声明、自定义 com.* 权限不算"},
    "R-MAN-03": {"name": "明文流量许可", "category": "M", "data_source": ["manifest", "res_decoded"], "max_status": STATUS_CONFIRMED, "priority": "P0",
                 "fp_notes": "未设置明文许可、或配置明确禁止明文的不算"},
    "R-MAN-04": {"name": "调试与备份风险", "category": "M", "data_source": ["manifest"], "max_status": STATUS_CONFIRMED, "priority": "P0",
                 "fp_notes": "allowBackup 显式为 false 且无 debuggable=true 的不算"},
    "R-MAN-05": {"name": "敏感广播监听", "category": "M", "data_source": ["manifest"], "max_status": STATUS_CONFIRMED, "priority": "P1",
                 "fp_notes": "自定义 action、非敏感系统事件的不算"},
    "R-PERM-01": {"name": "定时/后台结构 × 敏感权限", "category": "P", "data_source": ["smali_src"], "max_status": STATUS_CONFIRMED, "priority": "P0",
                  "fp_notes": "仅调度原语或仅敏感 API 单侧存在的不算；**档位按证据强度分档**："
                              "① 有调度→目标组件→敏感 API 调用链证据 → 已确认（结构事实）；"
                              "② 仅样本级共存、无可解析调度目标 → 待复核（疑点组合）；"
                              "两档均不得表述真实执行时间与实际滥用"},
    "R-PERM-02": {"name": "非交互组件使用敏感 API", "category": "P", "data_source": ["manifest", "smali_src"], "max_status": STATUS_CONFIRMED, "priority": "P0",
                  "fp_notes": "Activity 不算；仅字段/import 声明而无调用的不算"},
    "R-PERM-03": {"name": "声明与使用不一致", "category": "P", "data_source": ["manifest", "smali_src"], "max_status": STATUS_CONFIRMED, "priority": "P1",
                  "fp_notes": "声明与使用一致的不算。**按静态排除力分档**："
                              "① 样本无反射/JNI/动态加载等隐藏调用通道 → 已确认（措辞须限定"
                              "'在当前 APK 自有代码范围内未发现使用'）；"
                              "② 存在隐藏调用通道 → 待复核，并列明通道"},
    "R-STR-01": {"name": "硬编码凭据", "category": "S", "data_source": ["dex_strings", "res_decoded"], "max_status": STATUS_CONFIRMED, "priority": "P0",
                 "fp_notes": "无——形式匹配即事实（示例值/占位值照报），不因数据真伪或用途降级"},
    "R-STR-02": {"name": "内网/明文端点", "category": "S", "data_source": ["dex_strings", "res_decoded"], "max_status": STATUS_CONFIRMED, "priority": "P0",
                 "fp_notes": "公网 https 地址不算；公网 http 不在本条范围"},
    "R-CODE-01": {"name": "动态代码加载", "category": "C", "data_source": ["smali_src", "dex_strings"], "max_status": STATUS_CONFIRMED, "priority": "P0",
                  "fp_notes": "仅字符串中出现类名、无调用上下文的不算（弱证据上限=待复核）"},
    "R-CODE-02": {"name": "WebView 危险组合", "category": "C", "data_source": ["smali_src"], "max_status": STATUS_CONFIRMED, "priority": "P0",
                  "fp_notes": "仅启用 JS 而无接口注入/文件访问的不算（三要素不齐不算）"},
    "R-NET-01": {"name": "证书校验绕过结构", "category": "N", "data_source": ["smali_src"], "max_status": STATUS_CONFIRMED, "priority": "P0",
                 "fp_notes": "委托系统默认实现的正确校验、非空实现的不算"},
    "R-NET-02": {"name": "WebView SSL 错误忽略", "category": "N", "data_source": ["smali_src"], "max_status": STATUS_CONFIRMED, "priority": "P0",
                 "fp_notes": "调用 handler.cancel() 的正确实现不算；无 proceed 不算"},
}

ALL_RULE_IDS = list(RULE_META.keys())

# ---------------------------------------------------------------- 敏感权限清单
# 覆盖总档列举：录音/相机/定位/短信/通话/通讯录/无障碍/悬浮窗/安装包/查询所有包/自启动 + 少量明确高敏项
SENSITIVE_PERMISSIONS = {
    # 录音
    "android.permission.RECORD_AUDIO": "录音",
    "android.permission.CAPTURE_AUDIO_OUTPUT": "录音输出捕获",
    # 相机
    "android.permission.CAMERA": "相机",
    # 定位
    "android.permission.ACCESS_FINE_LOCATION": "精确定位",
    "android.permission.ACCESS_COARSE_LOCATION": "粗略定位",
    "android.permission.ACCESS_BACKGROUND_LOCATION": "后台定位",
    # 短信
    "android.permission.RECEIVE_SMS": "接收短信",
    "android.permission.SEND_SMS": "发送短信",
    "android.permission.READ_SMS": "读取短信",
    "android.permission.RECEIVE_MMS": "接收彩信",
    "android.permission.RECEIVE_WAP_PUSH": "接收WAP推送",
    # 通话
    "android.permission.READ_PHONE_STATE": "读取电话状态",
    "android.permission.CALL_PHONE": "拨打电话",
    "android.permission.ANSWER_PHONE_CALLS": "接听电话",
    "android.permission.READ_CALL_LOG": "读取通话记录",
    "android.permission.WRITE_CALL_LOG": "写通话记录",
    "android.permission.PROCESS_OUTGOING_CALLS": "处理拨出电话",
    "android.permission.READ_PHONE_NUMBERS": "读取本机号码",
    # 通讯录/账户
    "android.permission.READ_CONTACTS": "读取通讯录",
    "android.permission.WRITE_CONTACTS": "写通讯录",
    "android.permission.GET_ACCOUNTS": "获取账户列表",
    # 无障碍
    "android.permission.BIND_ACCESSIBILITY_SERVICE": "绑定无障碍服务",
    # 悬浮窗
    "android.permission.SYSTEM_ALERT_WINDOW": "悬浮窗",
    # 安装/卸载/包查询
    "android.permission.REQUEST_INSTALL_PACKAGES": "请求安装应用",
    "android.permission.INSTALL_PACKAGES": "安装应用",
    "android.permission.DELETE_PACKAGES": "卸载应用",
    "android.permission.QUERY_ALL_PACKAGES": "查询所有包",
    # 自启动
    "android.permission.RECEIVE_BOOT_COMPLETED": "开机自启动",
    # 使用统计/系统设置
    "android.permission.PACKAGE_USAGE_STATS": "应用使用统计",
    "android.permission.WRITE_SETTINGS": "修改系统设置",
    # Android 12/13+ 新增敏感权限（清单需随平台演进维护）
    "android.permission.READ_MEDIA_IMAGES": "读取图片",
    "android.permission.READ_MEDIA_VIDEO": "读取视频",
    "android.permission.READ_MEDIA_AUDIO": "读取音频",
    "android.permission.ACCESS_MEDIA_LOCATION": "读取媒体位置信息",
    "android.permission.NEARBY_WIFI_DEVICES": "附近 Wi-Fi 设备",
    "android.permission.BLUETOOTH_SCAN": "蓝牙扫描",
    "android.permission.BLUETOOTH_CONNECT": "蓝牙连接",
    "android.permission.BLUETOOTH_ADVERTISE": "蓝牙广播",
    "android.permission.BODY_SENSORS": "身体传感器",
    "android.permission.BODY_SENSORS_BACKGROUND": "后台身体传感器",
    "android.permission.ACTIVITY_RECOGNITION": "活动识别",
    "android.permission.MANAGE_EXTERNAL_STORAGE": "管理外部存储",
    "android.permission.USE_BIOMETRIC": "使用生物识别",
}

# 广播型权限：其"使用"体现在 manifest 的 Receiver/intent-filter，不做 R-PERM-03 过度声明判定
BROADCAST_TYPE_PERMISSIONS = {
    "android.permission.RECEIVE_BOOT_COMPLETED",
}

# ---------------------------------------------------------------- 敏感广播事件（R-MAN-05）
SENSITIVE_ACTIONS = {
    "android.intent.action.BOOT_COMPLETED": "开机完成",
    "android.intent.action.LOCKED_BOOT_COMPLETED": "开机完成(锁定阶段)",
    "android.provider.Telephony.SMS_RECEIVED": "短信接收",
    "android.provider.Telephony.WAP_PUSH_RECEIVED": "WAP推送",
    "android.intent.action.PHONE_STATE": "电话状态",
    "android.intent.action.NEW_OUTGOING_CALL": "拨出电话",
    "android.intent.action.USER_PRESENT": "用户解锁呈现",
    "android.intent.action.SCREEN_ON": "屏幕点亮",
    "android.intent.action.SCREEN_OFF": "屏幕熄灭",
    "android.net.conn.CONNECTIVITY_CHANGE": "网络变化",
    "android.intent.action.PACKAGE_ADDED": "应用安装",
    "android.intent.action.PACKAGE_REMOVED": "应用卸载",
    "android.intent.action.PACKAGE_REPLACED": "应用更新",
    "android.intent.action.PACKAGE_FULLY_REMOVED": "应用完全卸载",
    "android.intent.action.ACTION_POWER_CONNECTED": "电源连接",
    "android.intent.action.ACTION_POWER_DISCONNECTED": "电源断开",
    "android.provider.Telephony.SECRET_CODE": "密令码",
    "android.app.action.DEVICE_ADMIN_ENABLED": "设备管理器激活",
    "android.intent.action.MY_PACKAGE_REPLACED": "本应用更新",
    "android.os.action.DEVICE_IDLE_MODE_CHANGED": "设备空闲模式",
}

# ---------------------------------------------------------------- 调度原语（R-PERM-01 左要素）
SCHEDULING_PRIMITIVES = {
    "Landroid/app/AlarmManager;->set": "AlarmManager 定时",
    "Landroid/app/job/JobScheduler;->schedule": "JobScheduler 调度",
    "Landroidx/work/WorkManager;->enqueue": "WorkManager 调度",
    "Landroid/os/Handler;->postDelayed": "Handler 延时",
    "Landroid/os/Handler;->sendMessageDelayed": "Handler 延时消息",
    "Ljava/util/Timer;->": "Timer 定时",
    "Ljava/util/concurrent/ScheduledExecutorService;": "ScheduledExecutor",
    "Ljava/util/concurrent/Executors;->newScheduledThreadPool": "ScheduledExecutor 池",
    "Ljava/util/concurrent/Executors;->newSingleThreadScheduledExecutor": "ScheduledExecutor 单线程",
}

# ---------------------------------------------------------------- 敏感 API（R-PERM-01 右要素 / R-PERM-02 判定）
# 类级模式用类型描述符（无 "->"），配合"仅统计 invoke-/new-instance 行"过滤，避免漏掉构造引用行
SENSITIVE_APIS = {
    "Landroid/media/MediaRecorder;": ("录音", "RECORD_AUDIO"),
    "Landroid/media/AudioRecord;": ("录音", "RECORD_AUDIO"),
    "Landroid/location/LocationManager;->requestLocationUpdates": ("定位", "LOCATION"),
    "Landroid/location/LocationManager;->getLastKnownLocation": ("定位", "LOCATION"),
    "Landroid/hardware/Camera;": ("相机", "CAMERA"),
    "Landroid/hardware/camera2/CameraManager;->openCamera": ("相机", "CAMERA"),
    "Landroid/telephony/SmsManager;->sendTextMessage": ("短信", "SMS"),
    "Landroid/telephony/SmsManager;->sendMultipartTextMessage": ("短信", "SMS"),
    "Landroid/telephony/TelephonyManager;->getDeviceId": ("电话信息", "PHONE"),
    "Landroid/telephony/TelephonyManager;->getImei": ("电话信息", "PHONE"),
    "Landroid/telephony/TelephonyManager;->getSubscriberId": ("电话信息", "PHONE"),
    "Landroid/telephony/TelephonyManager;->getLine1Number": ("电话信息", "PHONE"),
    "Landroid/provider/ContactsContract;": ("通讯录", "CONTACTS"),
    "Landroid/content/ClipboardManager;->getPrimaryClip": ("剪贴板读取", "CLIPBOARD"),
    "Landroid/media/projection/MediaProjectionManager;->createScreenCaptureIntent": ("屏幕捕获", "SCREEN"),
    "Landroid/content/pm/PackageInstaller;": ("包安装器", "INSTALL"),
}

# ---------------------------------------------------------------- 声明即生效的权限（R-PERM-03 排除集）
# 这类权限无需调用对应 API，清单声明即生效，判"未发现使用"属误报。
# 来源：B 通道（mimo-v2.6-flash）复核观察 → 人工/规则采纳（B 提疑 → 规则改进闭环）。
DECLARATION_ONLY_PERMISSIONS = {
    "android.permission.QUERY_ALL_PACKAGES",      # 声明即获得包可见性
    "android.permission.SYSTEM_ALERT_WINDOW",     # 悬浮窗：系统按声明授予能力
    "android.permission.REQUEST_INSTALL_PACKAGES",  # 安装授权入口，无直接调用点
    "android.permission.MANAGE_EXTERNAL_STORAGE",  # 存储管理授权入口
    "android.permission.PACKAGE_USAGE_STATS",     # 使用情况授权入口
    "android.permission.WRITE_SETTINGS",          # 系统设置授权入口
    "android.permission.BIND_ACCESSIBILITY_SERVICE",  # 无障碍：声明后由系统绑定
}

# ---------------------------------------------------------------- 隐藏调用通道（R-PERM-03 静态排除力）
# 存在任一通道 → "代码中未发现使用"无法静态排除（运行时可绕过扫描）→ 结论停在待复核；
# 无任何通道 → 排除性结论的可信度提高，可升已确认（措辞必须带范围限定）。
HIDDEN_CHANNEL_PATTERNS = {
    "反射-类加载": "Ljava/lang/Class;->forName",
    "反射-方法获取": "Ljava/lang/Class;->getDeclaredMethod",
    "反射-方法调用": "Ljava/lang/reflect/Method;->invoke",
    "反射-字段访问": "Ljava/lang/reflect/Field;->get",
    "JNI-库加载": "Ljava/lang/System;->load",
    "动态加载-DexClassLoader": "Ldalvik/system/DexClassLoader;",
    "动态加载-PathClassLoader": "Ldalvik/system/PathClassLoader;",
    "动态加载-InMemoryDex": "Ldalvik/system/InMemoryDexClassLoader;",
}

# 权限 → 使用证据模式（R-PERM-03：检测"是否在自有代码中使用了该敏感权限"）
# 出现任一模式即视为"已发现使用"（宽松：宁可放过过度声明，不误报为过度声明）
PERMISSION_USAGE_PATTERNS = {
    "android.permission.RECORD_AUDIO": ["Landroid/media/MediaRecorder;->", "Landroid/media/AudioRecord;->"],
    "android.permission.CAPTURE_AUDIO_OUTPUT": ["Landroid/media/AudioRecord;->"],
    "android.permission.CAMERA": ["Landroid/hardware/Camera;->", "Landroid/hardware/camera2/", "Landroidx/camera/"],
    "android.permission.ACCESS_FINE_LOCATION": ["Landroid/location/LocationManager;->", "Lcom/google/android/gms/location/", "Landroid/location/FusedLocationProviderClient", "Landroid/location/LocationListener"],
    "android.permission.ACCESS_COARSE_LOCATION": ["Landroid/location/LocationManager;->", "Lcom/google/android/gms/location/", "Landroid/location/LocationListener"],
    "android.permission.ACCESS_BACKGROUND_LOCATION": ["Landroid/location/LocationManager;->", "Lcom/google/android/gms/location/"],
    "android.permission.RECEIVE_SMS": ["Landroid/telephony/SmsMessage;", "Landroid/provider/Telephony;"],
    "android.permission.SEND_SMS": ["Landroid/telephony/SmsManager;->"],
    "android.permission.READ_SMS": ["Landroid/provider/Telephony;", "Landroid/telephony/SmsMessage;"],
    "android.permission.RECEIVE_MMS": ["Landroid/telephony/SmsMessage;"],
    "android.permission.RECEIVE_WAP_PUSH": ["Landroid/telephony/SmsMessage;"],
    "android.permission.READ_PHONE_STATE": ["Landroid/telephony/TelephonyManager;->", "Landroid/telephony/SubscriptionManager;->"],
    "android.permission.CALL_PHONE": ["Landroid/telephony/TelecomManager;->", "Landroid/telephony/TelephonyManager;->", "android.intent.action.CALL"],
    "android.permission.ANSWER_PHONE_CALLS": ["Landroid/telephony/TelecomManager;->"],
    "android.permission.READ_CALL_LOG": ["Landroid/provider/CallLog;"],
    "android.permission.WRITE_CALL_LOG": ["Landroid/provider/CallLog;"],
    "android.permission.PROCESS_OUTGOING_CALLS": ["Landroid/telephony/TelecomManager;->"],
    "android.permission.READ_PHONE_NUMBERS": ["Landroid/telephony/TelephonyManager;->"],
    "android.permission.READ_CONTACTS": ["Landroid/provider/ContactsContract;->"],
    "android.permission.WRITE_CONTACTS": ["Landroid/provider/ContactsContract;->"],
    "android.permission.GET_ACCOUNTS": ["Landroid/accounts/AccountManager;->"],
    "android.permission.BIND_ACCESSIBILITY_SERVICE": ["Landroid/accessibilityservice/"],
    "android.permission.SYSTEM_ALERT_WINDOW": ["TYPE_APPLICATION_OVERLAY", "TYPE_SYSTEM_ALERT", "TYPE_PHONE", "Landroid/provider/Settings;->canDrawOverlays"],
    "android.permission.REQUEST_INSTALL_PACKAGES": ["Landroid/content/pm/PackageInstaller;->", "android.intent.action.INSTALL_PACKAGE", "Landroid/content/pm/PackageInstaller"],
    "android.permission.INSTALL_PACKAGES": ["Landroid/content/pm/PackageInstaller;->"],
    "android.permission.DELETE_PACKAGES": ["Landroid/content/pm/PackageInstaller;->"],
    "android.permission.QUERY_ALL_PACKAGES": ["Landroid/content/pm/PackageManager;->getInstalledPackages", "Landroid/content/pm/PackageManager;->getInstalledApplications", "Landroid/content/pm/PackageManager;->queryIntentActivities"],
    "android.permission.PACKAGE_USAGE_STATS": ["Landroid/app/usage/UsageStatsManager;"],
    "android.permission.WRITE_SETTINGS": ["Landroid/provider/Settings$System;->putString", "Landroid/provider/Settings$System;->putInt", "android.settings.action.MANAGE_WRITE_SETTINGS"],
}

# ---------------------------------------------------------------- 凭据模式（R-STR-01）
# 形式匹配即事实：示例值/形式值照报（bad02/bad04 真值口径），过滤与否交给人
CREDENTIAL_PATTERNS = [
    ("PEM 私钥", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    ("AWS Access Key", r"(?<![0-9A-Za-z])AKIA[0-9A-Z]{12,20}(?![0-9A-Za-z])"),
    ("GitHub Token", r"(?<![0-9A-Za-z_])ghp_[0-9A-Za-z]{20,}"),
    ("GitHub Token(旧)", r"(?<![0-9A-Za-z_])gho_[0-9A-Za-z]{20,}"),
    ("Slack Token", r"xox[baprs]-[0-9A-Za-z\-]{10,}"),
    ("Stripe Key", r"(?<![0-9A-Za-z_])sk_(?:test|live)_[0-9A-Za-z]{16,}"),
    ("Google API Key", r"(?<![0-9A-Za-z_\-])AIza[0-9A-Za-z_\-]{30,}"),
    ("阿里云 AccessKey", r"(?<![0-9A-Za-z])LTAI[0-9A-Za-z]{12,}"),
    ("腾讯云 SecretId", r"(?<![0-9A-Za-z])AKID[0-9A-Za-z]{26,}"),
    ("JWT", r"eyJ[0-9A-Za-z_\-]{8,}\.eyJ[0-9A-Za-z_\-]{8,}\.[0-9A-Za-z_\-]{8,}"),
]

# ---------------------------------------------------------------- 内网端点模式（R-STR-02）
INTERNAL_URL_PATTERN = (
    r"http://(?:" 
    r"10\.\d{1,3}\."
    r"|192\.168\."
    r"|172\.(?:1[6-9]|2\d|3[01])\."
    r"|127\."
    r"|0\.0\.0\.0"
    r"|localhost"
    r"|[A-Za-z0-9\-\.]+\.local"
    r"|[A-Za-z0-9\-\.]+\.internal"
    r")"
)

# ---------------------------------------------------------------- 钉证据：语义疑点 → 规则映射
# 机制（ADR-0004）：B 侧疑点必须映射到规则并经受该规则的机械判定核对，方可升级。
#   all_of: 各组关键词必须全部命中（组内任一命中即该组满足）；关键词匹配不区分大小写。
# 钉成功档位 = 该规则的 max_status（不得越过规则上限）；映射不到/机械未命中的 → 保持疑点。
PIN_RULE_MAP = {
    "R-MAN-01": {"all_of": [["导出", "exported", "暴露"],
                            ["permission", "权限", "保护"],
                            ["未", "无", "缺少", "缺", "没有", "未见", "未出现", "不存在", "missing"]],
                 "note": "组件导出且无权限保护（manifest 直证）"},
    "R-MAN-02": {"all_of": [["权限", "permission"]],
                 "note": "敏感权限声明（manifest 直证）"},
    "R-MAN-03": {"all_of": [["明文", "cleartext"]],
                 "note": "明文流量许可（manifest/资源直证）"},
    "R-MAN-04": {"all_of": [["debuggable", "调试", "备份", "backup", "allowbackup"]],
                 "note": "调试/备份配置（manifest 直证）"},
    "R-MAN-05": {"all_of": [["广播", "receiver", "boot", "sms_received", "phone_state"]],
                 "note": "敏感广播监听（manifest 直证）"},
    "R-PERM-01": {"all_of": [["定时", "调度", "后台", "alarmmanager", "postdelayed", "循环执行"]],
                  "note": "调度结构 × 敏感 API 共存（smali；档位上限=待复核）"},
    "R-PERM-02": {"all_of": [["service", "receiver", "provider", "后台组件", "非交互"]],
                  "note": "非交互组件内敏感 API 调用（smali）"},
    "R-PERM-03": {"all_of": [["过度声明", "未使用", "冗余权限", "声明了但"]],
                  "note": "权限声明与使用不一致（排除性结论；档位上限=待复核）"},
    "R-STR-01": {"all_of": [["凭据", "密钥", "私钥", "key", "token", "secret", "password", "密码",
                             "akia", "ghp_", "sk_", "jwt"]],
                 "note": "硬编码凭据形式匹配（原文检索回放）"},
    "R-STR-02": {"all_of": [["内网", "明文端点", "http://", "localhost", "192.168", "127.0.0.1",
                             "10.0.", "10.1.", "172.16", "172.17", "172.18", "172.19", "172.2", "172.30", "172.31"]],
                 "note": "内网/明文端点（原文检索回放）"},
    "R-CODE-01": {"all_of": [["动态加载", "dexclassloader", "pathclassloader", "插件", "loadclass",
                              "system.load", "inmemorydexclassloader"]],
                  "note": "动态代码加载调用（smali）"},
    "R-CODE-02": {"all_of": [["webview", "javascript", "js 接口", "js接口", "addjavascriptinterface"]],
                  "note": "WebView 危险组合（smali 三要素）"},
    "R-NET-01": {"all_of": [["证书", "trustmanager", "hostnameverifier", "校验绕过", "ssl 校验", "证书校验"]],
                 "note": "证书校验绕过结构（smali）"},
    "R-NET-02": {"all_of": [["ssl 错误", "sslerror", "ssl错误", "handler.proceed", "proceed"]],
                 "note": "WebView SSL 错误忽略（smali）"},
}

# ---------------------------------------------------------------- 第三方库前缀（自有代码反向判定用）
LIBRARY_PREFIXES = (
    "android/", "androidx/", "com/google/", "com/squareup/", "org/apache/", "org/intellij/",
    "org/jetbrains/", "kotlin/", "kotlinx/", "java/", "javax/", "dalvik/", "okhttp3/", "okio/",
    "retrofit2/", "com/facebook/", "io/reactivex/", "com/bumptech/", "org/json/", "org/xml/",
)

# ---------------------------------------------------------------- 自由文本扫描上限
MAX_SNIPPET_LEN = 200          # raw_snippet 截断长度
MAX_HITS_PER_RULE = 50         # 单规则命中上限（超出记录并截断）
DEX_SCAN_MAX_STRINGS = 200000  # 防御性上限

# ---------------------------------------------------------------- LLM 接入（通道 B / 评价器共用）
KEY_FILE_NAME = "key.txt"
LLM_TEMPERATURE = 0
LLM_MAX_TOKENS = 2048   # 推理模型（reasoning tokens 计入配额）需要余量，2026-10-14 实测调整
LLM_TIMEOUT_SECONDS = 90
LLM_RETRY = 1
LLM_RETRY_BACKOFF_SECONDS = 20   # 限流(429)/5xx 退避重试间隔（实测遇到过 429）

# 预算（项目取值，2026-10-14 经项目负责人调整为 30；课程试点建议值 10 为参考）
BUDGET_MAX_LLM_CALLS_PER_RUN = 30
BUDGET_MAX_REGISTERED_TESTS = 5

# ---------------------------------------------------------------- 工具链
APKTOOL_JAR_PREFIX = "apktool_"
APKTOOL_DECODE_TIMEOUT_SECONDS = 300
SUBPROCESS_ALLOWED_BINARIES = {"java", "java.exe"}

# 解码产物放工作区外临时区（总档 §10：工作区内写会显著拖慢 apktool）
DECODE_TMP_DIRNAME = "apkaudit_decode"


def is_sensitive_permission(name):
    """精确或后缀匹配（容忍不带 android.permission. 前缀的写法）。"""
    if not name:
        return False
    if name in SENSITIVE_PERMISSIONS:
        return True
    short = "android.permission." + name
    return short in SENSITIVE_PERMISSIONS
