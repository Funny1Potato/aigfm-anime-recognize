# aigfm-anime-recognize

二次元角色识别 HTTP 服务（WD14 打标，本地免费推理）。

给 [nonebot-plugin-aigf-master](https://github.com/Funny1Potato/nonebot-plugin-aigf-master)
的「二次元角色识别」功能提供后端：插件把图片发给本服务，返回角色标签
（Danbooru 风格 `角色名_(作品名)`）与画风分级。动漫和二次元手游角色共用同一套标签空间，
不需要训练、不需要自建图库。

## 特性

- 本地推理（ONNXRuntime，纯 CPU 即可），模型常驻约 **900MB 内存 / 446MB 磁盘 / 0.9s 每张**
- 单进程 + 单例模型 + 启动预热，并发按物理核心限流
- 结果按图片内容 SHA-256 缓存（默认 24h），同一张图重复请求不重复推理
- 可选 Bearer token 鉴权；GIF 自动取第一帧；图片大小上限 20MB

## 一键部署

```bash
# Windows
install.bat

# Linux / macOS
chmod +x install.sh && ./install.sh
```

脚本会：创建 `.venv` → 安装钉版本依赖 → 预热（首次运行从 HuggingFace 下载约 446MB 模型）→ 启动服务（`0.0.0.0:8000`）。

> 国内网络首次下载模型需走镜像：`install.bat` / `install.sh` 已默认设置 `HF_ENDPOINT=https://hf-mirror.com`，国外直连可注释掉对应行。

## 手动部署

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export HF_ENDPOINT=https://hf-mirror.com   # 国内必需
.venv/bin/python -c "from tagging import prewarm; prewarm()"   # 预热 + 下载模型
.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000
```

依赖钉版本原因见 `requirements.txt` 顶部注释（numpy<2 与 opencv 版本硬冲突、onnxruntime 需显式安装）。

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `RECOGNIZE_HOST` | `0.0.0.0` | 监听地址 |
| `RECOGNIZE_PORT` | `8000` | 监听端口 |
| `RECOGNIZE_TOKEN` | 空 | 非空时要求请求带 `Authorization: Bearer <token>` |
| `RECOGNIZE_CHARACTER_THRESHOLD` | `0.85` | 角色标签置信度阈值（模型只返回高于阈值的标签） |
| `RECOGNIZE_MAX_FILE_BYTES` | `20971520` | 单张图片大小上限（字节） |
| `RECOGNIZE_CACHE_TTL` | `86400` | 结果缓存 TTL（秒） |

## API

### `GET /health`

```json
{"status": "ok"}
```

### `POST /recognize`

两种传图方式：

```bash
# multipart file
curl -X POST http://127.0.0.1:8000/recognize -F "file=@samples/hutao.jpg"

# JSON base64
curl -X POST http://127.0.0.1:8000/recognize \
  -H "Content-Type: application/json" \
  -d '{"image": "<base64>", "character_threshold": 0.85}'
```

响应：

```json
{
  "characters": [["hu_tao_(genshin_impact)", 0.987]],
  "rating": {"general": 0.001, "sensitive": 0.888, "questionable": 0.107, "explicit": 0.000},
  "people_count": 1
}
```

- `characters`：角色标签按置信度降序；无命中为空数组
- `rating`：画风分级概率，插件侧用于 NSFW 标注
- `people_count`：从 general 特征提取的图中人数（Ngirls/Nboys 取最大），无数值标签为 `null`（单人图通常为 1）

## 模型与数据来源

本服务不自研模型，只是把开源模型封装成 HTTP 接口；识别能力与局限性均来自上游：

| 组件 | 来源 | 说明 |
|---|---|---|
| 打标模型 | [`SmilingWolf/wd-swinv2-tagger-v3`](https://huggingface.co/SmilingWolf/wd-swinv2-tagger-v3) | WD14 tagger 系列 v3，作者 **SmilingWolf**，许可 **Apache-2.0**；SwinV2 骨干，ONNX 格式 |
| 模型加载仓库 | [`deepghs/wd14_tagger_with_embeddings`](https://huggingface.co/deepghs/wd14_tagger_with_embeddings) | DeepGHS 的打包仓库（含上述 `model.onnx` 与配套 embeddings），`dghs-imgutils` 默认从此处加载 |
| 推理框架 | [`dghs-imgutils`](https://github.com/deepghs/imgutils)（[WD14 打标文档](https://dghs-imgutils.deepghs.org/main/api_doc/tagging/wd14.html)） | 纯 ONNXRuntime 实现；模块声明参考了 [SmilingWolf/wd-v1-4-tags](https://huggingface.co/spaces/SmilingWolf/wd-v1-4-tags) |
| 标签体系 | Danbooru | `角色名_(作品名)` 形式的 booru 标签，动漫与二次元手游共用同一套标签空间 |
| 训练数据 | Danbooru 图片（ID 取模 0000–0899），**标签更新至 2024-02-28** | 训练工具 [SmilingWolf/JAX-CV](https://github.com/SmilingWolf/JAX-CV)，TPU 由 Google TRC 提供 |

- 模型文件约 446MB，首次启动自动从 HuggingFace 下载到本地缓存，之后完全离线推理（不联网、不调用第三方 API）
- 模型许可为 **Apache-2.0**（以模型页为准）；本仓库只提供调用封装，不修改模型权重
- 上表「标签更新至 2024-02-28」正是下面第 1 条局限（新游/新角色认不出）的直接原因

## 已知局限

1. **训练数据截止 2024 年前后**（标签更新至 2024-02-28）：新游/新角色可能无标签，`characters` 为空
2. **多人同图会漏**：模型对整张图打标，多人合影可能只返回其中部分角色
3. **皮肤/异格不区分**：同一角色的泳装/节日限定/异格通常只给基础角色名
4. **3D 战斗小人 / 游戏内截图识别率明显偏低**，官方 2D 立绘最准
5. 输出是英文 booru 标签（如 `hu_tao_(genshin_impact)`），需要展示层做中文映射
