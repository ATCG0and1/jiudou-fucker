# 九斗 fucker

jiudou123.com 网安大作业，自动搞定 18 个单元课后题。

## 怎么发现的

瞎试的时候发现 `exercisesInfo` 这个接口在还没提交的情况下，直接把答案扔在 `sonSubList[].answer` 里返回了。离谱。所以根本不需要什么浏览器模拟、空提交再撤回那套，直接 http 请求就完事。

## 接口

全在 `api.guangyiedu.com/v3/`，所有请求都得带 `client=4&token=xxx&uid=xxx`，格式是 `application/x-www-form-urlencoded`。

### 拿单元列表
```
POST /v3/clazz/exercise/stu/exercisesPage
page=1&pagesize=50&client=4&token=&uid=
```
返回 `data.data[]`，每个有 `exercisesId`、`exercisesName`、`status`（0 就是没做）

### 拿题目和答案（这个就是漏洞接口）
```
POST /v3/tiku/exerciseStu/exercisesInfo
exerciseId=&client=4&token=&uid=
```
返回 `data.subjects[]`：
- `tSubject` 题型：1 单选 2 多选 4 填空 5 问答 11 组合题 14 判断
- `sonSubList[].answer` 正确答案就在这，有的会用 `^*` 隔开多个可接受答案
- `analyse` 是解析，html 格式的，正确答案用 `<u>` 包的

### 提交
```
POST /v3/tiku/exerciseStu/commitAnswer
exerciseId=&answers=<json>&client=4&token=&uid=
```
answers 大概长这样：
```json
[
  {"lang":"","subjectId":"292353"},
  {"lang":"","subjectId":"292354","stuAnswer":"host countries"},
  ...
]
```
组合题的父题不传 stuAnswer，只传子题的。返回 `code:200 msg:"提交成功"` 就行。如果返回"已经提交过了"得先调撤回。

### 撤回
```
POST /v3/tiku/v4/exerciseStu/withdraw
exercisesId=&client=4&token=&uid=
```

## 踩过的坑

- jiudou123.com 是个 Vue SPA，直接 http 请求拿到的就是个空壳，数据都是 api.guangyiedu.com 给的
- 九斗是光一教育的子品牌，所以 api 域名是 guangyiedu
- chunk.js 有 2.2MB 但那是 ECharts 和 ElementUI，真正业务代码在 webpack 动态加载的分块里
- Windows 终端编码是 gbk，脚本开头一定要 utf-8 wrapper
- "已经提交过了"返回的不是 200，要单独处理
- tSubject=2 的选择题，`answers[].isCorrect` 里 2 才是对的（1 是错的），看 `answer` 字段更直接
- tSubject=5 的问答，`answer` 是一大坨 html，有 `<p>` `<span>` 什么的，还带个 "Reference answer:" 前缀，要 strip 掉
- 服务器处理 json 里 `\n` 转义有 bug，所以问答答案只能搞成单行纯文本提交，不能带换行

## 脚本怎么跑

```powershell
# 自动模式（推荐给同学用）
双击启动.bat  # 自动装 venv + 开浏览器登录

# 手动模式
python jiudou_fucker.py --token "xxx" --uid 1234567
python jiudou_fucker.py --token "xxx" --uid 1234567 --force  # 强行全部重做
python jiudou_fucker.py --withdraw-only 24511 --token "xxx" --uid 1234567  # 撤回
```

## token 怎么拿

登录 jiudou123.com → F12 → Application → Cookies → 找到 token 这个 cookie，还有 stu_info 里面 url decode 之后有 uid
