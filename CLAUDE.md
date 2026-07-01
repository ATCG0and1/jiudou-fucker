# 九斗平台自动答题脚本

jiudou123.com 课后习题自动答题，网络安全课程项目。

## 漏洞

`exercisesInfo` 接口在用户未提交状态下就把正确答案放在 `sonSubList[].answer` 字段里返回了。纯 HTTP 请求就能拿到所有答案，不需要浏览器模拟、不需要先空提交再看答案那一套。

## API

基地址 `https://api.guangyiedu.com/v3/`，所有请求都要带 `client=4&token={token}&uid={uid}`，Content-Type 是 `application/x-www-form-urlencoded`。

### 获取单元列表

```
POST /v3/clazz/exercise/stu/exercisesPage
参数: page, pagesize, client, token, uid
```

返回 `data.data[]`，关注 `exercisesId`、`exercisesName`、`status`（0=未完成）。

### 获取题目和答案

```
POST /v3/tiku/exerciseStu/exercisesInfo
参数: exerciseId, client, token, uid
```

返回 `data.subjects[]`，每个题目：

| 字段 | 说明 |
|------|------|
| `tSubject` | 1=单选, 2=多选, 4=填空, 5=问答, 11=组合题, 14=判断 |
| `sonSubList[].answer` | 正确答案，多答案用 `^*` 分隔 |
| `analyse` | 解析，HTML 格式，正确答案在 `<u>` 标签里 |
| `answers[]` | 选择题的选项列表，`isCorrect`=2 表示正确 |

### 提交答案

```
POST /v3/tiku/exerciseStu/commitAnswer
参数: exerciseId, answers(JSON字符串), client, token, uid
```

answers JSON 示例：

```json
[
  {"lang":"","subjectId":"292353"},
  {"lang":"","subjectId":"292354","stuAnswer":"host countries"},
  {"lang":"","subjectId":"292365","stuAnswer":"A"}
]
```

组合题的父题（tSubject=11）只有 `subjectId`，不传 `stuAnswer`。子题带答案，填空传文字，选择传字母。

返回 `code:200 msg:"提交成功"` 表示成功。返回"已经提交过了"说明需要先撤回。

### 撤回

```
POST /v3/tiku/v4/exerciseStu/withdraw
参数: exercisesId, client, token, uid
```

## 两个脚本

`jiudou_auto.py` —— 给同学用的，Playwright 自动打开浏览器登录，提取 cookie 后全自动完成。依赖虚拟环境 + 国内镜像，启动.bat 一键搞定。

`jiudou_fucker.py` —— 自己调试用的，手动传 token 和 uid，不走浏览器。

## 注意事项

- jiudou123.com 是 Vue SPA，直接抓页面只能拿到空壳。数据都在 api.guangyiedu.com
- 九斗是光一教育的子品牌，所以 API 域名是 guangyiedu
- chunk.js 有 2.2MB，那是 ECharts 和 ElementUI 的库，业务代码在 webpack 按需加载的模块里（比如 7666.myCourse.js）
- Windows 终端默认编码是 GBK，脚本要在最前面把 stdout 包成 UTF-8
- "已经提交过了"返回的 code 不是 200，要单独 catch 然后调撤回再重试
- tSubject=5 的问答，answer 是一大段 HTML（`<p>`、`<span>` 什么的），前面还带 "Reference answer:"，需要 strip 掉标签和前缀
- 服务器对 JSON 里 `\n` 转义的处理有 bug，问答答案只能提交纯单行文本，不能带换行符

## 用法

```powershell
# 自动模式
双击 启动.bat

# 手动模式
python jiudou_fucker.py --token "xxx" --uid 1234567
python jiudou_fucker.py --token "xxx" --uid 1234567 --force
python jiudou_fucker.py --withdraw-only 24511 --token "xxx" --uid 1234567
```

## 获取 token

登录 jiudou123.com → F12 → Application → Cookies → 找 `token` 这个 cookie。`stu_info` URL decode 之后有 uid。
