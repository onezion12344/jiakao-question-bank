# jiakao-question-bank 驾考宝典题库

中国「驾考宝典」(jiakaobaodian.com) 官方题库的完整开源提取 — 科目一 & 科目四（安全文明常识），覆盖全部 9 种车型。

> 本仓库数据于 2026-11-16 通过驾考宝典公开 Web API 提取，仅供学习研究。版权归驾考宝典（北京木仓科技）所有，禁止商业使用。请支持正版 App。

## 数据

- `clean/{carType}-{course}.ndjson` — 每行一题（NDJSON），字段见下表
- `media/` — 全部题目配图（1,867 张，按文件名首字母分片，~100MB）
- `clean/media-manifest.json` — 配图 URL → 本地文件对照清单
- `index.json` — 各车型×科目的题量统计

### 字段说明

| 字段 | 说明 |
|---|---|
| `id` | 题目 ID（驾考宝典官方） |
| `carType` / `course` | 车型（car/bus/truck/moto/…）与科目（kemu1=科目一, kemu3=科目四） |
| `chapterId` | 章节号（题目所属知识分类） |
| `type` | 单选题 / 判断题 |
| `question` | 题干 |
| `options` | 选项数组 `[{letter, text}]` |
| `answer` | 答案字母数组（如 `["A"]` 或多选 `["A","C"]`） |
| `explain` | 完整解析 |
| `difficulty` / `wrongRate` | 官方难度与全站错误率 |
| `media` | 配图 URL（无图为 null） |

## 题量

| 车型 | 科目 | 题量 |
|---|---|---|
| 客车 | 科目一 | 2363 |
| 客车 | 科目四 | 747 |
| 小车(C1/C2/C3) | 科目一 | 1702 |
| 小车(C1/C2/C3) | 科目四 | 1416 |
| 出租车 | 从业资格证 | 500 |
| 货运 | 从业资格证 | 1078 |
| 教练员 | 从业资格证 | 1465 |
| 客运 | 从业资格证 | 1963 |
| 摩托车 | 科目一 | 513 |
| 摩托车 | 科目四 | 383 |
| 货车(A2/B2) | 科目一 | 2422 |
| 货车(A2/B2) | 科目四 | 2848 |
| 危化品 | 从业资格证 | 529 |

**合计 17929 题**，1,867 张配图（~100MB，`media/` 已本地化）。

## 复现

```bash
python3 crawl_jiakao.py   # 全量爬取（~25 分钟，9 车型 × 2 科目）
python3 build_repo.py     # 转换为干净 NDJSON
python3 crawl_media.py    # (可选) 下载全部题目配图
```

## 逆向说明

- 题目列表/详情：`api2.jiakaobaodian.com/api/open/question/*.htm`（2017 年公开接口，至今存活）
- 章节树/练习分组：`jk-tiku.kakamobi.cn/api/web/practise/*.htm`（Web 版前端在用）
- 唯一门槛是 `_r` 参数，非加密签名，算法：

```js
i = Math.abs(parseInt(Date.now() * Math.random() * 10000)).toString()
checksum = String(digitsum(i) + i.length).padStart(3, "0")
_r = "1" + i + checksum
```

- 批量详情接口 `question-list.htm` 用 POST 表单提交 `questionIds`，单次可携带 900+ ID。

## License

数据遵循原厂版权（仅限个人学习）；代码 MIT。
