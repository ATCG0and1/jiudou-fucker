# 九斗自动答题 (Jiudou Auto Answer)

九斗平台 (jiudou123.com) 课后习题自动化答题工具。

> **⚠️ 声明**：本项目仅用于学习研究目的（Web API 逆向分析、浏览器自动化技术实践），严禁用于任何形式的学术不端、作业代做或考试作弊。使用者需自行承担因违规使用产生的一切后果。

## 核心发现

九斗平台的 `exercisesInfo` API 在用户**未提交状态**下即返回所有题目的正确答案（含在 `sonSubList[].answer` 字段中），存在严重的数据泄露漏洞。

## 快速开始

1. 下载 `jiudou_auto.py`、`启动.bat`、`requirements.txt` 到同一文件夹
2. 双击 `启动.bat`
3. 浏览器自动打开 → 扫码/账号登录九斗
4. 终端按 Enter → 全自动完成

## 技术架构

```
API Base: https://api.guangyiedu.com/v3/

POST /clazz/exercise/stu/exercisesPage   → 获取单元列表
POST /tiku/exerciseStu/exercisesInfo     → 获取题目+答案
POST /tiku/exerciseStu/commitAnswer      → 提交答案
POST /tiku/v4/exerciseStu/withdraw       → 撤回提交
```

### 题目类型处理

| tSubject | 题型 | 处理方式 |
|----------|------|----------|
| 1, 2 | 单选/多选 | 提取选项字母 A/B/C/D |
| 4 | 填空题 | 提取答案文本 |
| 5 | 问答题 | 剥离 HTML 标签，取纯文本 |
| 11 | 组合题 | 父题跳过，遍历子题提交 |
| 14 | 判断题 | 提取 1/0 或 A/B |

### 关键技术点

- **Playwright** 启动系统浏览器（Chrome/Edge）自动提取 Cookie
- **虚拟环境** 隔离依赖，不污染系统 Python
- **国内镜像** pip 安装加速
- **自动撤回+重提交** 处理"已经提交过"的情况
- **限流重试** 处理服务器"正在处理请求"响应
- **HTML 答案剥离** 问答题的 `answer` 字段为 HTML 格式，自动 strip 并去 "Reference answer" 前缀

## 文件说明

| 文件 | 用途 |
|------|------|
| `jiudou_auto.py` | 主脚本 |
| `jiudou_fucker.py` | 备用脚本（手动 token 模式） |
| `启动.bat` | Windows 一键启动 |
| `CLAUDE.md` | 项目开发者文档 |
| `requirements.txt` | Python 依赖 |

## License

MIT License
