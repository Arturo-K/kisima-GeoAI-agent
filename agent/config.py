from langchain_ollama import ChatOllama
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any, List
from .tools import get_tools

class AgentConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    llm_model: str = "glm-4.6:cloud"
    temperature: float = 0.2

    def __init__(self):
        super().__init__()
        self._init_llm()
        self._init_tools()
    
    
    def _init_llm(self) -> ChatOllama:
        return ChatOllama(
            model=self.llm_model, 
            temperature=self.temperature)

    def _init_tools(self) -> List:
        return get_tools()

    @property
    def llm(self):
        return self._init_llm()

    @property
    def tools(self):
        return self._init_tools()