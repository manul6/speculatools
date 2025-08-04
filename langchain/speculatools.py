from langchain_core.tools import Tool
from langchain_core.runnables import Runnable
from typing import Dict, Any
from asyncio import create_task



async def call_tool(chain: Runnable, tool: Tool, tool_input: Dict[str, Any]):
    """
    >>> test_call_tool()
    """
    task = create_task(tool.arun(tool_input))
    async for chunk in chain.stream({"result" : {"status": "success"}}):
        yield chunk
        if task.done():
            break
    result = await task
    if result["status"] != "success":
        yield "<MISPREDICT>"
        async for chunk in chain.stream({"result" : result}):
            yield chunk

def test_call_tool():
    from langchain_core.tools import tool
    from time import sleep
    from asyncio import run

    import langchain
    langchain.debug = False
    
    @tool
    def slow_is_equal_to_one(x: int) -> dict:
        """slow tool that checks if input equals 1 and returns a dictionary."""
        sleep(1)
        if x == 1:
            return {"status": "success"}
        return {"status": "error"}
    
    class DummyChain(Runnable):
        def __init__(self, template: str):
            self.template = template
        def __ror__(self, other):
            self.input = other
            return self
        def invoke(self, input, config=None):
            return self.template.format(**input)
        async def stream(self, input):
            for chunk in self.template.format(**input):
                yield chunk
    
    TEMPLATE_MSG = "answer to x == 1: {result}" 
    TRUE_MSG = TEMPLATE_MSG.format(result={"status": "success"})
    FALSE_MSG = TEMPLATE_MSG.format(result={"status": "error"})
    
    async def _test_for(*, x):
        chain = DummyChain(TEMPLATE_MSG)
        result = call_tool(chain, slow_is_equal_to_one, {"x": x})
        output_str = ""
        async for chunk in result:
            output_str += chunk
        return output_str

    def _correct_finally(*, predict, misprediction_token="<MISPREDICT>", truth) -> bool:
        guesses = predict.split(misprediction_token)
        if len(guesses) == 1:
            return guesses[0] == truth # no mispredictions
        elif len(guesses) == 2:
            return (predict.startswith(guesses[0])  # at first we were wrong
                    and truth == guesses[1])  # then corrected ourselves
        else:
            raise ValueError("too many mispredictions") # TODO: we could just implement this though

    one_result = run(_test_for(x=1))
    assert _correct_finally(predict=one_result, truth=TRUE_MSG)
    two_result = run(_test_for(x=2))
    assert _correct_finally(predict=two_result, truth=FALSE_MSG)