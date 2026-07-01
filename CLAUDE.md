# 九斗平台自动答题脚本 (jiudou_fucker)

## 项目概述

jiudou123.com 网络安全大作业 —— 自动化完成九斗平台 18 个单元的课后习题。

## 核心发现

**API 泄露漏洞：`exercisesInfo` 接口在未提交状态下直接将正确答案放在 `sonSubList[].answer` 字段返回。** 因此完全不需要浏览器自动化或"空提交→解析→撤回"流程，纯 HTTP API 即可完成所有答题。

## API 文档

### 基础信息

- **前端**: `https://www.jiudou123.com` (Vue SPA)
- **API 基地址**: `https://api.guangyiedu.com/v3/`
- **认证方式**: Cookie `token` + `uid` 作为请求参数
- **请求格式**: `application/x-www-form-urlencoded;charset=UTF-8`
- **公共参数**: 所有请求必须带 `client=4&token={token}&uid={uid}`

### 接口列表

#### 1. 获取单元列表
```
POST /v3/clazz/exercise/stu/exercisesPage
Body: page=1&pagesize=50&client=4&token=xxx&uid=xxx
```
返回 `data.data[]` 数组，每个元素：
- `exercisesId`: 习题模板ID（用于后续接口）
- `exercisesName`: 单元名称如 "《军事英语》Unit 19"
- `status`: 0=未完成, 非0=已完成
- `classId`, `id`: 其他标识

#### 2. 获取题目和答案（核心接口）
```
POST /v3/tiku/exerciseStu/exercisesInfo
Body: exerciseId={exercisesId}&client=4&token=xxx&uid=xxx
```
返回 `data.subjects[]` 数组，每个题目包含：
- `subjectId`: 题目ID
- `tSubject`: 题型（1=单选, 2=多选, 4=填空, 11=组合题, 14=判断）
- `parentId`: 父题ID（"0"=顶级题）
- `status`: 0=待答, 2=已答对, 3=未答, 4=部分作答
- `answer`: 正确答案（非组合题）
- `sonSubList[]`: 子题列表（组合题的子题或填空题的每个空）
  - `subjectId`: 子题ID
  - `answer`: **正确答案！**（多答案用 `^*` 分隔，如 "Secretary General^*Secretary-General"）
  - `tSubject`: 4=填空题, 选择题型(A/B/C/D)
- `analyse`: 解析（HTML格式，答案用 `<u>` 标签标注）
- `score`: 分值

#### 3. 提交答案
```
POST /v3/tiku/exerciseStu/commitAnswer
Body: answers={URL-encoded JSON}&exerciseId=xxx&client=4&token=xxx&uid=xxx
```
`answers` JSON 格式:
```json
[
  {"lang":"","subjectId":"292353"},           // 组合题父题，无 stuAnswer
  {"lang":"","subjectId":"292354","stuAnswer":"host countries"},  // 子题
  {"lang":"","subjectId":"292355","stuAnswer":"legitimacy"},
  ...
  {"lang":"","subjectId":"292364"},           // 下一个组合题的父题
  {"lang":"","subjectId":"292365","stuAnswer":"A"},
  ...
]
```
- 父题（tSubject=11）：只有 `subjectId`，没有 `stuAnswer`
- 子题：`subjectId` + `stuAnswer`（填文字或 A/B/C/D）
- 返回 `{"code":200,"msg":"提交成功"}` 表示成功
- 返回 `"已经提交过了"` 表示需先撤回

#### 4. 撤回提交
```
POST /v3/tiku/v4/exerciseStu/withdraw
Body: exercisesId={exercisesId}&client=4&token=xxx&uid=xxx
```
撤回后状态回到"未答"，可重新提交。

### 题型映射

| tSubject | 类型 | stuAnswer 格式 | 备注 |
|----------|------|---------------|------|
| 1 | 单选题 | "A" | |
| 2 | 多选题/判断题 | "A,B" 或 "A" | T/F题选项为A/B |
| 4 | 填空题 | "答案文字" | |
| 5 | 问答题 | 纯文本（剥HTML后） | answer 字段含完整 HTML 范文，需 strip |
| 11 | 组合题 | 无（通过子题提交） | 子题 tSubject=2/4 |
| 14 | 判断题 | "1" 或 "0" | |

### 关键陷阱
- **tSubject=5 的 answer 是 HTML**：`<p style="..."><span>Reference answer: ...</span></p>`，必须 strip HTML 标签后再提交
- **isCorrect=2 才是正确答案**：`answers[].isCorrect` 中 1=错, 2=对
- **多可接受答案用 `^*` 分隔**：如 `"Secretary General^*Secretary-General"`

### answer 字段格式
- 单答案: `"host countries"`
- 多可接受答案: `"Secretary General^*Secretary-General"` （`^*` 分隔，取第一个即可）

## 脚本架构

### 文件
- `jiudou_fucker.py` —— 主脚本

### 数据结构
```
Exercise (单元)
  ├── exercises_id, name, status
  └── questions: List[Question]

Question (题目)
  ├── subject_id, t_subject, title, score, status, answer
  └── son_sub_list: List[SubQuestion]

SubQuestion (子题/填空)
  ├── subject_id, answer, status
  └── get_best_answer() → 取 ^* 分隔的第一个答案
```

### 控制流
```
fuck_all()
  → get_exercise_list()        # 获取所有单元
  → for each exercise:
      fuck_exercise(exercises_id)
        → get_exercise_info()   # 获取题目+答案
        → submit_answers()      # 构造JSON提交
          → 如果"已经提交过" → withdraw() → 重新 submit_answers()
```

### 使用
```powershell
# 完成所有单元
python jiudou_fucker.py --token "xxx" --uid 1234567

# 只做指定单元
python jiudou_fucker.py --exercise-id 24511 --token "xxx" --uid 1234567

# 强制重做已完成单元
python jiudou_fucker.py --token "xxx" --uid 1234567 --force

# 撤回指定单元
python jiudou_fucker.py --withdraw-only 24511 --token "xxx" --uid 1234567
```

### 获取 token 和 uid
1. 登录 https://www.jiudou123.com
2. F12 → Application → Cookies → www.jiudou123.com
3. `token` → Cookie 值
4. `stu_info` → URL decode → JSON 中的 `uid` 字段

## 踩坑记录

1. **不要用 WebFetch 或 HTTP 直接请求 jiudou123.com** —— 返回的是 Vue SPA 空壳，实际数据通过 api.guangyiedu.com 获取
2. **不要用 Bash** —— Windows 环境，统一用 PowerShell
3. **Windows 控制台编码** —— 需要在脚本开头设置 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`
4. **"已经提交过了" 是 code!=200 的错误响应** —— 需要特殊处理，先撤回再重提
5. **API 域名是 api.guangyiedu.com（光一教育）** —— 九斗是光一教育的子品牌
6. **JS 文件混淆** —— chunk.js 2.2MB 是 ECharts/ElementUI 库，业务代码在 webpack 分块加载的页面模块中（如 7666.myCourse.js）
