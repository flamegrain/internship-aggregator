# 🎓 实习信息聚合器 (Internship Aggregator)

[![React](https://img.shields.io/badge/Frontend-React-61DAFB?logo=react&logoColor=white)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Tailwind CSS](https://img.shields.io/badge/Styling-Tailwind--CSS-38B2AC?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Deployed on Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?logo=vercel&logoColor=white)](https://internship-aggregator-nu.vercel.app/)

[English](./README.md) | [简体中文] | 🌐 **在线演示**: [internship-aggregator-nu.vercel.app](https://internship-aggregator-nu.vercel.app/)

一个功能强大的全栈实习信息聚合平台，旨在帮助学生发现、筛选并追踪心仪的实习机会。聚合了来自**10家顶级公司**和社区源的**1,500+实习职位**。特别针对 2026 年夏季实习周期进行了优化。

---

## 📖 项目概述

**Internship Aggregator** 是一个现代化的 Web 应用程序，解决了实习信息碎片化的问题。它能自动从可信源收集职位列表，通过智能标签进行处理，并在简洁、可搜索的界面中展示。

无论您是在寻找 AI/ML 特定职位，还是想了解公司对国际学生（H1B/签证支持）的友好程度，该工具都能为您提供一目了然的见解。

## 🚀 核心特性

- 🕷️ **自动化爬虫**：与高质量的实习仓库实时同步。
- 🔍 **高级筛选**：按公司、职位、地点或行业搜索，即时获取结果。
- 🤖 **AI 职位高亮**：自动识别并标记与人工智能和机器学习相关的职位。
- 🌍 **国际学生关注**：包含“友好度评分”（1-10），指示签证赞助的可能性。
- ⚡ **极简 UI**：基于 Tailwind CSS 的响应式设计，提供无缝的桌面和移动端体验。
- 📊 **一键申请**：直接跳转至申请页面，节省您的时间。

## 📂 丰富的数据生态系统

Internship Aggregator 的核心竞争力在于其**无与伦比的数据丰富度**。我们从多样化的网络中汇总高质量列表，确保您不会错过任何机会。

### 🌟 主要数据来源

我们从社区驱动的高质量源和官方职业门户汇总数据：

| 来源类型 | 来源名称 | 更新频率 | 描述 |
|-------------|-------------|------------------|-------------|
| **社区** | [SimplifyJobs GitHub](https://github.com/SimplifyJobs/Summer2026-Internships) | **实时** | 最大的社区驱动实习仓库。 |
| **官方** | [高盛 (Goldman Sachs)](https://www.goldmansachs.com/careers) | **爬取** | 高盛官方实习项目。 |
| **官方** | [苹果 (Apple Careers)](https://jobs.apple.com) | **爬取** | 苹果公司的工程与运营实习。 |
| **官方** | [Meta Careers](https://www.metacareers.com) | **爬取** | Meta 旗下应用的实习机会。 |
| **官方** | [NASA STEM](https://stemgateway.nasa.gov) | **爬取** | NASA 官方 STEM 实习机会。 |
| **官方** | [微软 (Microsoft)](https://apply.careers.microsoft.com) | **API** | 实时获取微软官方职业 API 数据。 |
| **官方** | [摩根大通 (JPMC)](https://www.jpmorganchase.com/careers) | **爬取** | 摩根大通技术项目与实习。 |
| **官方** | [摩根士丹利 (MS)](https://www.morganstanley.com/careers) | **API** | 摩根士丹利学生技术项目。 |
| **官方** | [谷歌 (Google Careers)](https://www.google.com/about/careers) | **爬取** | 谷歌软件、硬件和研究实习。 |
| **官方** | [亚马逊 (Amazon Jobs)](https://www.amazon.jobs) | **爬取** | 亚马逊工程和商业实习。 |

### 🔍 自动化爬虫架构

我们的数据采集引擎针对不同源采用了不同的技术方案：

- **直接 API 集成**：针对微软和摩根士丹利，我们直接对接其内部职业 API，确保速度和数据准确性。
- **浏览器自动化 (Playwright)**：针对苹果、Meta 和摩根大通等动态网站，我们使用无头浏览器模拟用户操作进行数据抓取。
- **Markdown 解析**：针对 GitHub 上的社区列表，我们解析原始 Markdown 文件以提取结构化数据。

## 🛠️ 技术栈

- **前端**: React (Vite), Tailwind CSS, Lucide Icons.
- **后端**: FastAPI (Python), SQLModel (ORM), Uvicorn.
- **数据库**: SQLite (本地存储，易于配置)。
- **自动化**: Playwright (浏览器自动化), BeautifulSoup/Requests (HTML 解析)。

## ⚙️ 快速开始

### 1. 后端设置
```bash
# 克隆仓库
git clone https://github.com/flamegrain/internship-aggregator.git
cd internship-aggregator

# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r backend/requirements.txt

# 填充数据库（可选）
python backend/crawler.py

# 启动服务器
uvicorn backend.main:app --reload
```
- API 地址: `http://127.0.0.1:8000`
- 文档地址: `http://127.0.0.1:8000/docs`

### 2. 前端设置
```bash
cd frontend
npm install
npm run dev
```
- 应用地址: `http://localhost:5173`

## 📁 项目结构
```text
internship-aggregator/
├── backend/            # FastAPI & 爬虫逻辑
│   ├── main.py         # 入口文件
│   ├── models.py       # SQLModel 定义
│   └── crawler.py      # 爬虫实现
├── frontend/           # React 应用
│   └── src/            # 组件与逻辑
└── README.md
```

---

## 🤝 参与贡献
欢迎贡献！请随时提交 Pull Request。

## 📄 开源协议
本项目采用 MIT 协议。
