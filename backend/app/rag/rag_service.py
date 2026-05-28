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

# RAG提示词模板 —— 归因强制 + 反幻觉约束
RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是严格的知识库助手，仅基于提供的文档片段回答问题。

## 必须遵守的规则
1. **归因强制**：每个关键事实陈述必须标注来源，格式为 [来源：片段N]
2. **禁止编造**：如果某个信息在你的训练数据中存在，但在文档片段中找不到，绝对不能输出
3. **不确定即标注**：无法100%确认的信息，必须说明"文档未明确记载"
4. **拒绝推断**：不要基于文档的只言片语推断完整结论，缺失就是缺失

## 什么时候必须回答"文档未提及"
- 问题要求的数字、日期、名称在文档中完全找不到
- 问题涉及的概念、事件、人物在文档中没有任何出现
- 问题需要跨文档因果推理，但文档只提供了孤立片段

## 判定"文档未提及"之前必须做的检查
在输出"文档未记载/未提及"之前，**必须**逐项确认：
1. 已逐一审查所有提供的 `[片段1]`、`[片段2]`…`[片段N]`，确认每个片段中确实不存在相关信息
2. 如果问题包含明确的多部分结构（如"三个阶段""三个方案""几个步骤"），每个部分都必须独立对照所有片段进行检索
3. 只有当你确认**所有片段**中确实不存在**任何**相关信息时，才能声明"未记载"
4. 如果发现某个片段包含部分相关信息但不够完整，应陈述已有信息，然后说明"文档对此未提供更多细节"

## 回答格式
先给出基于文档的答案（带来源标注），然后在末尾简要说明哪些信息在文档中找不到（如有）。

## 输出质量要求
- 核心原则：**信息完整性优先于文本简洁性**。宁可稍显冗余，不可遗漏关键信息。
- 区分标准：不同阶段、不同时间点、不同参与方的不同方案，**属于不同事实**，必须分别陈述。
  判断"是否重复"的唯一标准：两个陈述是否指向文档中**同一句话描述的同一具体事件**。
  示例："第一阶段的气象屏障方案"和"第三阶段的基因编辑方案"虽然都属防御措施，但它们是不同事实——不是重复。
- 同一来源的同一事实只陈述一次，但不同来源的互补信息应整合呈现。"""),
    ("user", """以下是从知识库检索到的文档片段：

{context}

用户问题：{question}

请严格按照上述规则回答。""")
])


class RAGService:
    """RAG查询服务 —— 检索 + 生成"""

    def __init__(self):
        self.retriever = HybridRetriever()
        self.model = get_chat_model()
        self.chain = RAG_PROMPT | self.model

    async def query(self, question: str, stream: bool = False):
        """执行RAG查询 —— 先检索再生成"""
        enhanced_query = preprocess_query(question)

        # 检索相关文档
        docs = await self.retriever.retrieve(enhanced_query)
        if not docs:
            docs = await vector_store_service.search_knowledge(enhanced_query)

        # 空结果兜底：不送入LLM，直接返回
        if not docs:
            return {
                "answer": "知识库中未找到相关信息，无法回答此问题。",
                "sources": [],
            }

        # 编号文档片段，支持归因标注 [来源：片段N]
        fragments = []
        for i, doc in enumerate(docs, start=1):
            fragments.append(f"[片段{i} 开始]\n{doc.page_content}\n[片段{i} 结束]")
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

            return {"answer": answer, "sources": [d.metadata for d in docs]}


# 全局单例
rag_service = RAGService()
