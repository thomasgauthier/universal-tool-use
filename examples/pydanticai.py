import asyncio
from dataclasses import dataclass
from typing import Dict
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
import os
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIModel


client = AsyncOpenAI(
    base_url="http://localhost:8001", 
    api_key="anystring"
)

model = OpenAIModel('deepseek-reasoner', openai_client=client)

class MockDatabase:
    def __init__(self):
        self._customers: Dict[int, Dict] = {
            123: {
                'name': 'John',
                'balance': 123.45,
            }
        }

    async def customer_name(self, id: int) -> str:
        return self._customers[id]['name']

    async def customer_balance(self, id: int, include_pending: bool = False) -> float:
        return self._customers[id]['balance']


@dataclass
class SupportDependencies:  
    customer_id: int
    db: MockDatabase


class SupportResult(BaseModel):  
    support_advice: str = Field(description='Advice returned to the customer')
    block_card: bool = Field(description="Whether to block the customer's card")
    risk: int = Field(description='Risk level of query', ge=0, le=10)


support_agent = Agent(  
    model,  
    deps_type=SupportDependencies,
    result_type=SupportResult,  
    system_prompt=(  
        'You are a support agent in our bank, give the '
        'customer support and judge the risk level of their query.'
    ),
)


@support_agent.system_prompt  
async def add_customer_name(ctx: RunContext[SupportDependencies]) -> str:
    customer_name = await ctx.deps.db.customer_name(id=ctx.deps.customer_id)
    return f"The customer's name is {customer_name!r}"


@support_agent.tool  
async def customer_balance(
    ctx: RunContext[SupportDependencies], include_pending: bool
) -> float:
    """Returns the customer's current account balance."""  
    return await ctx.deps.db.customer_balance(
        id=ctx.deps.customer_id,
        include_pending=include_pending,
    )


...  


async def main():
    deps = SupportDependencies(customer_id=123, db=MockDatabase())
    result = await support_agent.run('What is my balance?', deps=deps)  
    print(result.data)  
    """
    support_advice='Hello John, your current account balance, including pending transactions, is $123.45.' block_card=False risk=1
    """

    result = await support_agent.run('I just lost my card!', deps=deps)
    print(result.data)
    """
    support_advice="I'm sorry to hear that, John. We are temporarily blocking your card to prevent unauthorized transactions." block_card=True risk=8
    """

if __name__ == "__main__":
    asyncio.run(main())