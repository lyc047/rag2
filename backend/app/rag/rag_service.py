"""RAG查询服务 —— 检索知识库文档并生成回答"""
import re
from langchain_core.prompts import ChatPromptTemplate
from app.utils.factory import get_chat_model
from app.rag.retriever import HybridRetriever
from app.rag.vector_store import vector_store_service
from app.rag.query_processor import preprocess_query
from app.core.logger import logger


def _clean_repetition(text: str) -> str:
    """清理生成文本中的表面重复（正则兜底）"""
    # 连续2-6字的词组重复3次及以上："根据根据根据" → "根据"
    text = re.sub(r'(.{2,6})\1{2,}', r'\1', text)
    # 连续重复的单字4次及以上："的的的的" → "的"
    text = re.sub(r'(.)\1{3,}', r'\1', text)
    return text

# RAG提示词模板 —— 归因强制 + 反幻觉约束 + 内部推理 + 信息边界 + 自然语言输出
RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是严格的知识库助手，仅基于提供的文档片段回答问题。

## 内部推理流程（全程在脑中完成，绝对禁止输出到最终回答中）
在开始写回答之前，你在内部做以下分析（这些不写入最终回答）：
1. 逐片段扫描，标出与问题直接相关的事实及其片段编号
2. 检查问题的每个子部分是否都有文档支撑，记录缺口
3. 区分"文档明确写的"和"需要推断的"
4. 确定哪些结论有完整支撑，哪些需要说明"未记载"

## 输出铁律 —— 最终回答中绝对禁止出现的元语言
你的最终回答是一段给用户看的自然语言文本。以下内容**一个字都不能出现**：
- "正在搜索……"、"经过检查发现……"、"根据片段N……"、"需要修正……"、"原回答无需修改"
- "第一步……第二步……"、"事实提取："、"完整性检查："、"边界确认："
- "我们"、"我注意到"、"我认为"、"经过分析"
- 任何形式的推理过程叙述、步骤编号、自问自答
- 任何括号内的自我评价如"（此信息来自片段3）"
- Markdown代码块、分点列表的"-"或"*"符号

## 归因的唯一正确方式
用 `[来源：片段N]` 标注，紧跟在所涉及的事实句后面，作为句子的自然组成部分。
示例：牛奶市的前身是白河镇[来源：片段1]，2005年升格为县级市[来源：片段1]。

## 必须遵守的规则
1. **归因强制**：每个关键事实陈述后标注 [来源：片段N]
2. **禁止编造**：训练数据中有但文档片段中没有的信息，绝对不能输出
3. **不确定即标注**：无法100%确认的信息，说明"文档未明确记载"
4. **拒绝推断**：不基于只言片语推断完整结论

## 信息边界
1. 文档说"A属于B类别" ≠ A有B的所有特征，不传递属性
2. 特例不泛化，部分不代表整体
3. 文档指明时间范围的，回答中保留时间限定，不把阶段性描述说成永久状态
4. 允许整合同一文档不同段落的明确陈述，禁止用外部知识填补逻辑空白
5. 关键数字、日期、专有名称直接引述文档原话

## 判定"文档未提及"的前置检查（内部完成，不输出检查过程）
声明"未记载"前，必须内部确认：已逐一审查所有片段 → 每个子问题独立对照 → 确认所有片段均无相关信息。如果某片段有部分信息但不完整，先陈述已有信息，再说明"文档对此未提供更多细节"。

## 输出格式
你的回答应是一个自然、流畅、完整的段落（或多个自然段落）。像一个人在给另一个人讲解一样。禁止任何形式的内部推理过程泄露。

结构：
1. 先给出基于文档的答案，自然嵌入来源标注
2. 有缺失时，在末尾自然地说明（如"关于X方面，文档未提供更多细节"）

## 语言质量标准
- 用自然的口语化书面语，读起来像一篇短文而非技术报告
- 避免重复表述同一事实，不同来源的互补信息整合到同一段落
- 关键信息完整优先于极度简洁。但同一事实不翻来覆去说多遍。"""),
    ("user", """以下是从知识库检索到的文档片段：

{context}

用户问题：{question}

请直接给出你的回答（一个完整、自然、干净的段落，不含任何推理过程）。""")
])


class RAGService:
    """RAG查询服务 —— 检索 + 生成 + 格式化输出"""

    def __init__(self):
        self.retriever = HybridRetriever()
        self.model = get_chat_model()
        self.chain = RAG_PROMPT | self.model

    async def _polish_answer(self, raw_answer: str, question: str) -> str:
        """后处理清洗 —— 调用LLM剥离推理过程，只保留干净的自然语言回答"""
        polish_prompt = f"""你的任务是把一段RAG系统的原始输出改写为干净、自然、可读的回答。

## 原始输出（可能混杂了推理过程、元语言、碎片化陈述）
{raw_answer}

## 用户原始问题
{question}

## 改写规则（严格执行）
1. 删除所有推理过程、检查步骤、内部思考——只保留最终结论
2. 删除所有元语言：如"正在搜索""经过检查""第一步""第二步""事实提取""完整性检查"等
3. 删除所有括号内的自评注：如"（此信息来自片段3）""（需要修正）"等
4. 保留 [来源：片段N] 标注——它们对可信度很重要
5. 将碎片化的陈述整合为连贯的段落，去除重复表述
6. 用自然的口吻写，像人在给另一个人讲解
7. 不要添加原始输出中没有的新信息
8. 如果原始输出的大部分都是推理过程而几乎没有实质内容，就提取出那一点点实质内容，用自然语言重新组织

## 输出
直接给出改写后的干净回答，不要加任何前缀说明（如"改写后："）。"""

        try:
            polished = await self.model.ainvoke(polish_prompt)
            result = polished.content if hasattr(polished, "content") else str(polished)
            return _clean_repetition(result)
        except Exception:
            logger.warning("回答清洗失败，回退到原始输出")
            return raw_answer  # 清洗失败时回退

    async def query(self, question: str, stream: bool = False):
        """执行RAG查询 —— 先检索再生成"""
        enhanced_query = preprocess_query(question)

        # 检索相关文档（非流式路径启用LLM重排序）
        docs = await self.retriever.retrieve(enhanced_query, rerank=not stream)
        if not docs:
            docs = await vector_store_service.search_knowledge(enhanced_query)

        # 空结果兜底：不送入LLM，直接返回
        if not docs:
            return {
                "answer": "知识库中未找到相关信息，无法回答此问题。",
                "sources": [],
            }

        # 编号文档片段，支持归因标注 [来源：片段N]
        # 附带可用时间元数据（如有），帮助LLM区分历史描述与现状
        fragments = []
        for i, doc in enumerate(docs, start=1):
            meta = doc.metadata
            time_tags = []
            if meta.get("content_time_range"):
                time_tags.append(f"内容时间范围：{meta['content_time_range']}")
            if meta.get("file_mtime"):
                time_tags.append(f"文件修改时间：{meta['file_mtime']}")
            header = f"[片段{i} 开始]"
            if time_tags:
                header += f" ({'; '.join(time_tags)})"
            fragments.append(f"{header}\n{doc.page_content}\n[片段{i} 结束]")
        context = "\n\n".join(fragments)

        if stream:
            return self.chain.astream({"context": context, "question": question})
        else:
            result = await self.chain.ainvoke({"context": context, "question": question})
            answer = _clean_repetition(result.content)

            # 遗漏自检：答案声称"未记载"时，做二次检索验证
            omission_keywords = ["未提及", "未记载", "未找到", "文档中不包含", "没有提供"]
            if any(kw in answer for kw in omission_keywords):
                verify_docs = await vector_store_service.search_knowledge(question, top_k=3)
                if verify_docs:
                    verify_fragments = []
                    for j, d in enumerate(verify_docs, start=1):
                        verify_fragments.append(f"[补充片段{j}]\n{d.page_content}")
                    verify_context = "\n\n".join(verify_fragments)
                    verify_prompt = f"""你之前给出的回答中包含了"未记载"或"未提及"的声明。现在系统为你提供了补充检索结果。请重新审查：

## 补充检索结果
{verify_context}

## 你之前的回答
{answer}

## 请执行以下检查
1. 补充片段中是否包含你之前声称"未记载"的信息？
2. 如果有，请修正回答，补充遗漏的信息
3. 如果确实没有，简要说明为什么补充片段也不包含相关信息
4. 如果原回答不需要修改，直接回复"原回答无需修改"即可"""
                    try:
                        correction = await self.model.ainvoke(verify_prompt)
                        answer = _clean_repetition(correction.content)
                        docs.extend(verify_docs)
                    except Exception:
                        pass  # 自检失败不影响主流程

            # 格式化清洗 —— 剥离推理过程，输出干净的自然语言回答
            answer = await self._polish_answer(answer, question)

            return {"answer": answer, "sources": [d.metadata for d in docs]}


# 全局单例
rag_service = RAGService()
