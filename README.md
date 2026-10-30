# 板块资金流向实时监控

基于东方财富数据接口的 A 股概念板块资金流实时监控工具，支持盘中实时抓取、可视化展示、历史数据存储和5日连续走势分析。

## 功能特性

- **实时抓取**：每15秒自动抓取全部500+概念板块资金流数据
- **可视化展示**：ECharts 动态曲线图，红涨绿跌，一目了然
- **自选板块**：自定义关注板块，金色高亮显示，永久保存
- **TOP20/LOW20**：一键切换流入/流出前20板块曲线
- **今日/5日连续**：支持查看当日实时走势和近5个交易日连续趋势
- **数据库存储**：SQLite 本地数据库，历史数据永久保存
- **零依赖部署**：Python 环境即可运行，无需数据库服务

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动抓取

```bash
python fetch_fund_flow.py
```

程序会自动判断交易时段（9:25~11:32, 12:58~15:05），非交易时段自动等待。

### 3. 打开可视化页面

用 Chrome / Edge 浏览器直接打开 `fund_flow_chart.html` 即可。

> 注意：因为浏览器读取本地 JSON 文件有跨域限制，建议在项目目录起一个简易HTTP服务：
> ```bash
> python -m http.server 8080
> ```
> 然后访问 http://localhost:8080/fund_flow_chart.html

## 项目结构

```
├── fetch_fund_flow.py      # 主程序：数据抓取 + 数据库存储
├── fund_flow_chart.html     # 可视化页面（ECharts）
├── requirements.txt         # Python 依赖
└── README.md
```

## 数据说明

### 接口来源
东方财富公开数据接口：`push2.eastmoney.com/api/qt/clist/get`

### 数据字段
| 字段 | 含义 |
|---|---|
| 主力净流入 | 主力资金当日累计净流入（亿元） |
| 超大单 | 超大单净流入（亿元） |
| 大单 | 大单净流入（亿元） |
| 中单 | 中单净流入（亿元） |
| 小单 | 小单净流入（亿元） |

### 自动生成文件
运行后在同目录自动生成：
- `fund_flow.db` — SQLite 数据库，所有历史数据
- `fund_flow_data.json` — 今日实时数据快照
- `chart_data_5d.json` — 近5个交易日连续数据

## 自定义配置

编辑 `fetch_fund_flow.py` 顶部配置区：

```python
FETCH_INTERVAL = 15     # 抓取间隔（秒）
```

自选板块在页面上直接输入关键词添加，存在浏览器 localStorage 中。

## 技术栈

- **后端**：Python 3 + Requests + SQLite
- **前端**：HTML + ECharts 5 + 原生 JavaScript
- **数据源**：东方财富公开行情接口

## 免责声明

本工具仅供学习研究使用，数据来源于公开渠道，不作为投资建议。股市有风险，投资需谨慎。
