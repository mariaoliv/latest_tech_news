from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage,AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.types import Send
from tavily import TavilyClient
import os
import json
from typing import List, Annotated
import operator
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
import uuid

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class QueryHint(BaseModel):
    query_hint: str = Field("a single executable search query that can be used to serch for in-depth information about a topic")

class QueryHints(BaseModel):
    query_hints: List[QueryHint] = Field("a list of 1-3 search queries for a particular topic")

class Topic(BaseModel):
    topic: str = Field("a short, specific description of the topic")
    keywords: List[str] = Field("a list of keywords (such as names of comapnies, people, and technologies)")
    urls: List[str] = Field("the urls of search results")
    query_hints: QueryHints

class Topics(BaseModel):
    topics: List[Topic]

class AgentState(MessagesState):
    news_topics: Topics
    raw_news_results: Annotated[list, operator.add]
    completed_topic_summaries: Annotated[
        list, operator.add
    ]
    final_summary: str

class WorkerState(MessagesState):
    completed_topic_summaries: Annotated[
        list, operator.add
    ]
    topic: Topic

def search_latest_tech_news(max_results: int = 15):
    """
    Perform web search to get the hottest tech news this week.
    Args:
    max_results: the max number of search results
    """
    try:
        tavily_client = TavilyClient(TAVILY_API_KEY)
        res = tavily_client.search(query="hottest tech news", search_depth="advanced", max_results=max_results, topic="news", time_range="week")
        return res["results"]
    except Exception as e:
        print(f"Exception occured: {e}")
        return None

def fetch_initial_results(state:AgentState):
    llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o-mini")
    structured_llm = llm.with_structured_output(Topics)
    results = search_latest_tech_news()

    prompt = """
    Given the results of a web search for the latest technology news, extract a list of **specific, concrete news topics**.

Each topic should:
- Describe a **single, well-defined news event or development**, not a broad theme.
- Be phrased as a short, precise description (not a headline rewrite).
- Be grounded in one or more of the provided search results.
- Include relevant keywords (e.g., companies, people, products, technologies).
- Include the URLs of the search results that support the topic.
- Include 1-3 concise query hints that would be useful for researching this topic in more depth.

Avoid:
- Vague or generic topics (e.g., “AI is growing,” “tech regulation updates”).
- Combining multiple unrelated events into one topic.
- Inventing information not present in the search results.

Return only the structured list of topics in the required format.
    """

    msgs = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Here are the search results: {results}")
    ]

    res = structured_llm.invoke(input=msgs)

    keys_to_keep = ["title", "url"]
    results = [{k:result[k] for k in keys_to_keep} for result in results]

    return {"raw_news_results": results, "news_topics": res}


def dedpuplicate(state: AgentState):
    
    llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o-mini")
    structured_llm = llm.with_structured_output(Topics)

    prompt = """
    You are a careful editor whose task is to deduplicate a list of news topics.

You will be given a JSON list of topic objects. Each topic represents a specific news event and includes evidence (such as article titles, URLs, or source IDs).

Your goal is to return a **deduplicated list of topics** by conservatively merging topics that clearly describe the **same underlying news event**.

### Rules (follow strictly)
- **Do NOT invent new topics.**
- **Do NOT add new facts, entities, or events.**
- You may only **keep**, **drop**, or **merge** topics that already exist in the input.
- Only merge topics if they are clearly about the **same event or story**, even if phrased differently.
- If two topics are related but describe **different events**, keep them separate.
- Prefer the **most specific and informative wording** when choosing the canonical topic.
- When merging topics:
  - Combine and preserve **all evidence** from the merged topics.
  - Preserve relevant entities.
- If there are no duplicates, return the list unchanged.
- The output must be a **subset or merge of the input topics**, never a rewritten or generalized summary.

### What counts as a duplicate
Two topics should be merged if they:
- Refer to the same companies/products/people **and**
- Describe the same concrete development (e.g., launch, delay, lawsuit, regulation change, earnings result).

Differences in phrasing alone do NOT make topics distinct.

### Output requirements
- Return the final deduplicated list using the provided structured schema.
- Do not include explanations, comments, or analysis.
- The output must be valid JSON and match the expected structure exactly.

    """

    current_topics = json.dumps(state.get("news_topics").model_dump())

    msgs = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Here are the current topics: {current_topics}")
    ]
    res = structured_llm.invoke(msgs)
    return {"news_topics": res}

def in_depth_search(query:str, max_results:int=4):
    tavily_client = TavilyClient(TAVILY_API_KEY)
    try:
        tavily_client = TavilyClient(TAVILY_API_KEY)
        search_results = tavily_client.search(query=query, search_depth="advanced", max_results=max_results, topic="news", include_raw_content=True, time_range="week")
        return search_results["results"]
    except Exception as e:
        print(f"Exception occured: {e}")
        return None

def search_topic_and_write_summary(state: WorkerState):
    topic = state.get("topic").topic
    query_hints = state.get("topic").query_hints.query_hints
    queries = [q.query_hint for q in query_hints]
    results = []
    flat_results = []
    for query in queries:
        search_results = in_depth_search(query)
        results.append(search_results)
        flat_results.extend(search_results)
    results_str = json.dumps(results)
    
    llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o-mini")
    prompt = """
    Given a specific news topic and a set of search results related to that topic, write a concise, well-structured summary of the **key findings**.

Requirements:
- Use **Markdown** formatting.
- Include a clear **title** that reflects the topic.
- Write a **body** that synthesizes the most important facts and developments from the search results.
- Base all statements on the provided sources; do not invent information.
- Focus on what is new, notable, or impactful about the topic.

Avoid:
- Rewriting individual articles verbatim.
- Speculation or unsupported conclusions.
- Unnecessary background unless it helps explain the significance.

Return only the markdown-formatted summary.

    """

    msgs = [
        SystemMessage(content=prompt),
        HumanMessage(f"Topic: {topic}\nSearch results: {results_str}")
    ]
    res = llm.invoke(msgs)
    keys_to_keep = ["title", "url"]
    results = [{k:result[k] for k in keys_to_keep} for result in flat_results]
    return {"completed_topic_summaries": [res.content], "messages": [res], "raw_news_results": results}

def create_final_summary(state: AgentState):
    final_summary = "\n\n".join(state.get("completed_topic_summaries"))
    
    #use LLM to create citations based on state["raw_news_results"]
    prompt = """
    You are given a list of web search results that were used as sources for a report.

Create a **References / Citations** section for the report based only on these results.

Requirements:
- Include only sources that appear in the provided search results.
- Each citation should correspond to a distinct source.
- Use a clear, consistent citation format suitable for a technical or research-style report.
- Include, when available: title, publisher or source name, and URL.
- Do not invent sources or add information not present in the search results.

Output:
- Return a Markdown-formatted list of citations (e.g., a bulleted list or numbered list).
- Do not include explanations or commentary—only the citations section.

    """
    raw_search_results = state.get("raw_news_results")

    msgs = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Here are the search results: {raw_search_results}")
    ]
    llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o-mini")
    citations = llm.invoke(msgs).content
    final_summary += f"\n\n{citations}"

    return {"final_summary": final_summary}

def assign_workers(state: AgentState):
    topics = state.get("news_topics").topics
    return [Send("search_topic_and_write_summary", {"topic": t}) for t in topics]

builder = StateGraph(AgentState)

builder.add_node("fetch_initial_results", fetch_initial_results)
builder.add_node("deduplicate", dedpuplicate)
builder.add_node("search_topic_and_write_summary", search_topic_and_write_summary)
builder.add_node("create_final_summary", create_final_summary)

builder.add_edge(START, "fetch_initial_results")
builder.add_edge("fetch_initial_results", "deduplicate")
builder.add_conditional_edges(
    "deduplicate", assign_workers, ["search_topic_and_write_summary"]
)
builder.add_edge("search_topic_and_write_summary", "create_final_summary")
builder.add_edge("create_final_summary", END)

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

# thread_id = str(uuid.uuid4())
# config = {
#     "configurable" : {
#         "thread_id" : thread_id
#     }
# }
# state = AgentState(messages=[HumanMessage(content="Summarize the latest tech news")])
# result = graph.invoke(state, config)
# print(result.get("final_summary"))
# print(result.get("messages"))