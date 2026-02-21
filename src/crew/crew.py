"""CrewAI crew for stock analysis using YAML-based agent and task definitions."""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from src.core.config.llm import get_llm
from src.crew.tools.calculator import FinancialCalculatorTool
from src.crew.tools.csv_reader import CSVReaderTool
from src.crew.tools.search import create_search_tool


@CrewBase
class StockAnalysisCrew:
    """Stock analysis crew — 6 agents, 6 tasks, sequential execution."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self):
        self.csv_reader = CSVReaderTool()
        self.calculator = FinancialCalculatorTool()
        self.search_tool = create_search_tool()
        self.llm = get_llm()

    # ── Agents ──────────────────────────────────────────────

    @agent
    def ratio_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["ratio_analyst"],
            tools=[self.csv_reader, self.calculator],
            llm=self.llm,
            verbose=True,
        )

    @agent
    def performance_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["performance_analyst"],
            tools=[self.csv_reader, self.calculator],
            llm=self.llm,
            verbose=True,
        )

    @agent
    def fundamental_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["fundamental_analyst"],
            tools=[self.csv_reader, self.calculator],
            llm=self.llm,
            verbose=True,
        )

    @agent
    def sentiment_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["sentiment_analyst"],
            tools=[self.csv_reader, self.search_tool],
            llm=self.llm,
            verbose=True,
        )

    @agent
    def market_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["market_reviewer"],
            tools=[self.csv_reader],
            llm=self.llm,
            verbose=True,
        )

    @agent
    def investment_advisor(self) -> Agent:
        return Agent(
            config=self.agents_config["investment_advisor"],
            tools=[],
            llm=self.llm,
            verbose=True,
        )

    # ── Tasks ───────────────────────────────────────────────

    @task
    def analyze_valuation_ratios(self) -> Task:
        return Task(config=self.tasks_config["analyze_valuation_ratios"])

    @task
    def analyze_price_performance(self) -> Task:
        return Task(config=self.tasks_config["analyze_price_performance"])

    @task
    def analyze_financial_health(self) -> Task:
        return Task(config=self.tasks_config["analyze_financial_health"])

    @task
    def analyze_market_sentiment(self) -> Task:
        return Task(config=self.tasks_config["analyze_market_sentiment"])

    @task
    def review_analysis(self) -> Task:
        return Task(config=self.tasks_config["review_analysis"])

    @task
    def generate_investment_report(self) -> Task:
        return Task(config=self.tasks_config["generate_investment_report"])

    # ── Crew ────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
