"""WD14 二次元角色打标封装（接收 bytes，供 HTTP 服务调用）"""

from __future__ import annotations

import re
from typing import Any


def tag_characters(
    image_bytes: bytes,
    character_threshold: float = 0.85,
    general_threshold: float = 0.35,
    model_name: str | None = None,
) -> dict[str, Any]:
    """对单张图片打标，返回插件侧需要的结构化结果。

    - characters: [[角色标签, 置信度], ...]（按置信度降序，
      如 [["hu_tao_(genshin_impact)", 0.987], ...]；无命中为空列表）
    - rating: 画风分级概率 {"general", "sensitive", "questionable", "explicit"}
    - people_count: 从 general 特征提取的图中人数（Ngirls/Nboys 取最大），
      无数值标签时为 None

    阈值是传给模型的：模型只返回高于阈值的标签，不要在返回后再过滤。
    """
    from imgutils.tagging import get_wd14_tags

    kwargs: dict[str, Any] = {
        "character_threshold": character_threshold,
        "general_threshold": general_threshold,
    }
    if model_name:
        kwargs["model_name"] = model_name

    rating, features, chars = get_wd14_tags(image_bytes, **kwargs)

    hits = sorted(
        ((str(name), float(score)) for name, score in (chars or {}).items()),
        key=lambda kv: -kv[1],
    )
    return {
        "characters": hits,
        "rating": rating or {},
        "people_count": extract_people_count(features or {}),
    }


def extract_people_count(features: dict[str, float]) -> int | None:
    """从 WD14 general 特征中提取图中人数。

    WD14 会输出 1girl/2girls/4boys 这类计数标签；多标签并存时取最大 N。
    multiple_girls/multiple_boys（无数值）不处理，返回 None。
    """
    best: int | None = None
    for name in features:
        m = re.fullmatch(r"(\d+)(girls?|boys?)", name)
        if m:
            n = int(m.group(1))
            if best is None or n > best:
                best = n
    return best


def prewarm() -> None:
    """生成一张小图触发模型下载/加载，把冷启动成本移到启动阶段。"""
    import io

    from PIL import Image

    img = Image.new("RGB", (64, 64), (255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    tag_characters(buf.getvalue())
