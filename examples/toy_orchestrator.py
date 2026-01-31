#!/usr/bin/env python3
"""
Toy Orchestrator Example
========================

A minimal, runnable orchestrator demonstrating:
- 2 tools (calculator, echo)
- 1 router (intent detection)
- 1 memory stub (conversation history)
- 1 decision loop (orchestrate → execute → respond)
- Safe math via AST-based evaluator (no eval)

Run: python examples/toy_orchestrator.py

Philosophy alignment:
- Bounded Memory: Only keeps last 10 messages
- Receipts: Prints trace of every decision
- Defaults Off: No persistence without explicit flag
- Local-First: No network calls (pure Python)
"""

import json
import os
import sys
from typing import Dict, List, Any
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.router import RuleRouter, Rule
from src.tool_registry import ToolRegistry, ToolSpec
from src.tools.math import evaluate_expression, SafeMathError


class ToyMemory:
    """Bounded conversation memory (max 10 messages)"""
    
    def __init__(self, max_messages: int = 10):
        self.messages: List[Dict[str, str]] = []
        self.max_messages = max_messages
    
    def add(self, role: str, content: str) -> None:
        """Add message and enforce bound"""
        self.messages.append({"role": role, "content": content, "timestamp": datetime.utcnow().isoformat()})
        if len(self.messages) > self.max_messages:
            # Forget oldest (bounded memory principle)
            self.messages.pop(0)
            print(f"  🗑️  [Memory] Forgot oldest message (cap: {self.max_messages})")
    
    def get_recent(self, n: int = 5) -> List[Dict[str, str]]:
        """Retrieve last N messages"""
        return self.messages[-n:]
    
    def summary(self) -> str:
        """Memory receipt"""
        return f"{len(self.messages)}/{self.max_messages} messages"


def calculator(expression: str) -> str:
    """Evaluate math expression using AST-safe evaluator."""
    try:
        result = evaluate_expression(expression)
        return f"Result: {result}"
    except SafeMathError as exc:
        return f"Error: {str(exc)}"


def echo(message: str) -> str:
    """Echo message back"""
    return f"Echo: {message}"


class ToyOrchestrator:
    """Main orchestration loop"""
    
    def __init__(self, memory_size: int = 10):
        self.memory = ToyMemory(max_messages=memory_size)
        self.tools = ToolRegistry()
        self.tools.register(ToolSpec(name="calculator", description="Evaluate math expression", handler=calculator))
        self.tools.register(ToolSpec(name="echo", description="Echo message back", handler=echo))

        self.router = RuleRouter()
        self.router.add_rule(
            Rule(
                tool="calculator",
                predicate=lambda text: any(word in text.lower() for word in ["calculate", "math", "+", "-", "*", "/"]),
                param_builder=lambda text: {
                    "expression": text.split("calculate")[-1].strip()
                    if "calculate" in text.lower()
                    else text
                },
                confidence=0.8,
                reason="keyword_math",
            )
        )
        self.router.add_rule(
            Rule(
                tool="echo",
                predicate=lambda text: any(word in text.lower() for word in ["echo", "repeat", "say"]),
                param_builder=lambda text: {
                    "message": text.split("echo")[-1].strip()
                    if "echo" in text.lower()
                    else text
                },
                confidence=0.9,
                reason="keyword_echo",
            )
        )
        self.trace: List[Dict[str, Any]] = []
    
    def process(self, user_input: str) -> str:
        """
        Orchestration loop:
        1. Add user message to memory
        2. Route to tool (or direct response)
        3. Execute tool if needed
        4. Generate response
        5. Add response to memory
        6. Return response + trace
        """
        print(f"\n📥 User: {user_input}")
        
        # Step 1: Store user message (bounded memory)
        self.memory.add("user", user_input)
        
        # Step 2: Route
        routing_decision = self.router.route(user_input)
        self._add_trace("routing", {
            "tool": routing_decision.tool,
            "params": routing_decision.params,
            "confidence": routing_decision.confidence,
            "reason": routing_decision.reason,
        })
        print(f"  🧭 [Router] Tool={routing_decision.tool}, Confidence={routing_decision.confidence}")
        
        # Step 3: Execute tool (if routed)
        if routing_decision.tool:
            tool_name = routing_decision.tool
            params = routing_decision.params
            tool_result = self.tools.execute(tool_name, **params)
            self._add_trace("tool_execution", {"tool": tool_name, "params": params, "result": tool_result})
            print(f"  🔧 [Tool] {tool_name}() → {tool_result}")

            response = tool_result.get("result") if tool_result.get("status") == "ok" else tool_result.get("error")
        else:
            # Direct response (no tool)
            response = f"I heard: '{user_input}'. Try asking me to calculate something or echo a message!"
            print(f"  💬 [Direct] No tool needed")
        
        # Step 4: Store response (bounded memory)
        self.memory.add("assistant", response)
        
        # Step 5: Print receipt
        print(f"  📊 [Memory] {self.memory.summary()}")
        print(f"📤 Assistant: {response}")
        
        return response
    
    def _add_trace(self, event_type: str, data: Dict[str, Any]) -> None:
        """Add event to trace (receipts principle)"""
        self.trace.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "data": data
        })
    
    def get_trace(self) -> List[Dict[str, Any]]:
        """Return full trace (receipts over assertions)"""
        return self.trace
    
    def print_trace_summary(self) -> None:
        """Print trace summary"""
        print("\n📋 Trace Summary:")
        for i, event in enumerate(self.trace, 1):
            print(f"  [{i}] {event['event']} @ {event['timestamp']}")


def interactive_demo():
    """Interactive CLI demo"""
    print("=" * 60)
    print("  TOY ORCHESTRATOR - Interactive Demo")
    print("=" * 60)
    print("\nCommands:")
    print("  - 'calculate 2 + 2' → Use calculator tool")
    print("  - 'echo hello' → Use echo tool")
    print("  - 'trace' → Show decision trace")
    print("  - 'memory' → Show conversation history")
    print("  - 'quit' → Exit")
    print("\nPhilosophy:")
    print("  ✓ Bounded Memory (10 messages max)")
    print("  ✓ Receipts (every decision traced)")
    print("  ✓ Local-First (no network)")
    print("=" * 60)
    
    orchestrator = ToyOrchestrator(memory_size=10)
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == "quit":
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == "trace":
                orchestrator.print_trace_summary()
                continue
            
            if user_input.lower() == "memory":
                recent = orchestrator.memory.get_recent(5)
                print(f"\n📚 Recent Memory (last 5 of {orchestrator.memory.summary()}):")
                for msg in recent:
                    print(f"  [{msg['role']}] {msg['content']}")
                continue
            
            # Process through orchestrator
            orchestrator.process(user_input)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def automated_demo():
    """Automated demo (non-interactive)"""
    print("=" * 60)
    print("  TOY ORCHESTRATOR - Automated Demo")
    print("=" * 60)
    
    orchestrator = ToyOrchestrator(memory_size=10)
    
    # Test cases
    test_inputs = [
        "calculate 2 + 2",
        "echo hello world",
        "what time is it?",  # No tool match
        "calculate 10 * 5 + 3",
        "echo this is a test",
    ]
    
    for user_input in test_inputs:
        orchestrator.process(user_input)
    
    # Print final trace
    orchestrator.print_trace_summary()
    
    print("\n" + "=" * 60)
    print(f"✅ Demo Complete: {len(test_inputs)} interactions processed")
    print(f"📊 Memory: {orchestrator.memory.summary()}")
    print(f"📋 Trace Events: {len(orchestrator.trace)}")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        automated_demo()
    else:
        interactive_demo()
