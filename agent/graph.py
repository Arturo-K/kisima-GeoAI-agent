import logging
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent

from .config import AgentConfig
from .prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """Minimal state - only what's needed."""
    messages: Annotated[List[BaseMessage], add_messages]
    query: str
    response: str
    location: Optional[tuple]
    markers: Optional[List[Dict]]
    metadata: Dict[str, Any]

def agent_node(state: AgentState, config: AgentConfig) -> Dict[str, Any]:
        """Process query through ReAct agent."""
        try:            
            agent = create_agent(
                model = config.llm,
                system_prompt = SYSTEM_PROMPT,
                tools = config.tools,
            )

            # Agent processes messages and appends AI response
            result = agent.invoke({"messages": state["messages"]})
            return {"messages": result["messages"]}
        except Exception as e:
            error_msg = f"Agent error: {str(e)}"
            return {"messages": [AIMessage(content=error_msg)]}

def extract_data_node(state: AgentState, config: AgentConfig) -> Dict[str, Any]:
    """Extract structured data from conversation."""
    location = None
    markers = []
    tools_used = []
        
    # Scan messages for tool calls and data
    for msg in state["messages"]:
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_name = tool_call.get('name')
                if tool_name not in tools_used:
                    tools_used.append(tool_name)
                    
                # Extract location from building searches
                if tool_name == 'search_buildings_by_location':
                    args = tool_call.get('args', {})
                    if (lat := args.get('latitude')) and (lon := args.get('longitude')):
                        location = (float(lat), float(lon))
            
            # Extract markers from infrastructure results
            if isinstance(msg, AIMessage) and '"items"' in msg.content:
                try:
                    data = json.loads(msg.content)
                    if isinstance(data, dict) and 'items' in data:
                        markers = [{
                            'coords': item['coords'],
                            'popup': f"{item.get('name', 'Unknown')} ({item.get('type', 'N/A')})",
                            'color': 'red' if item.get('risk_level') == 'high' else 'blue',
                            'icon': 'info-sign'
                        } for item in data['items'][:10]]
                except json.JSONDecodeError:
                    pass
        
    # Get final response from last AI message
    response = next(
        (msg.content for msg in reversed(state["messages"]) if isinstance(msg, AIMessage)),
        "No response generated."
    )
        
    return {
        "response": response,
        "location": location,
        "markers": markers or None,
        "metadata": {
            'messages_count': len(state["messages"]),
                'has_tool_calls': len(tools_used) > 0,
                'tools_used': tools_used
            }
        }

def build_graph(config: AgentConfig) -> StateGraph:
    if not config:
        config = AgentConfig()
    
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", lambda state: agent_node(state, config))
    workflow.add_node("extract_data", lambda state: extract_data_node(state, config))

    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", "extract_data")
    workflow.add_edge("extract_data", END)

    logger.info("Woop Woop !!! Graph built successfully")
    
    return workflow.compile(checkpointer=MemorySaver())