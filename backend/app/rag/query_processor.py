"""查询预处理 —— 关键词提取、短查询扩展，提升检索精度"""
import re
from app.core.logger import logger

# 中文常见停用词（高频但无语义价值的词）
_STOP_WORDS = {
    '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一',
    '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有',
    '看', '好', '自己', '这', '他', '她', '它', '们', '那', '些', '吗', '呢',
    '吧', '啊', '哦', '嗯', '哈', '呀', '啦', '哇', '么', '什么', '怎么', '哪',
    '可以', '应该', '可能', '已经', '还是', '或者', '因为', '所以', '但是',
    '然后', '虽然', '不过', '而且', '如果', '只能', '还有', '不会', '不能',
    '这个', '那个', '哪个', '这里', '那里', '这样', '那样', '什么样', '怎么',
}


def is_short_query(query: str) -> bool:
    """判断是否为过短查询（< 5个有效字符）"""
    clean = re.sub(r'[^一-鿿\w]', '', query)
    return len(clean) < 5


def extract_keywords(query: str) -> str:
    """提取关键词 —— 按标点切分后去除停用词"""
    words = re.split(r'[，,。.！!？?\s、；;：:（）()【】\[\]《》<>""''""+-]+', query)
    keywords = [w for w in words if w and w not in _STOP_WORDS]
    return ' '.join(keywords) if keywords else query


def preprocess_query(query: str) -> str:
    """查询预处理 —— 提取关键词用于BM25检索增强"""
    if not query or not query.strip():
        return query

    query = query.strip()

    # 短查询：混入关键词提取版本，增强BM25命中率
    if is_short_query(query):
        kw = extract_keywords(query)
        if kw and kw != query:
            enhanced = f"{query} {kw}"
            logger.info(f"短查询增强: '{query}' → '{enhanced}'")
            return enhanced

    return query
