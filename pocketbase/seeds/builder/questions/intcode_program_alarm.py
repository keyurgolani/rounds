"""Intcode Program Alarm — Medium. Array, Simulation, Interpreter.

A minimal Intcode VM with three opcodes. The key insight is that
parameters are addresses, not immediate values — reading them as
raw numbers produces plausible but wrong results.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Intcode Program Alarm",
    "difficulty": "Medium",
    "description": (
        "Implement a tiny Intcode interpreter. Given `program`, process opcode `1` as addition, opcode `2` as "
        "multiplication, and opcode `99` as halt. Each arithmetic opcode reads two input positions and one output "
        "position from the next three cells. Return the final memory state."
    ),
    "hints": [
        "Clone the input before mutating it so callers do not see side effects.",
        "Treat the three parameters after opcode 1 or 2 as addresses, not immediate values.",
        "Opcode 1 adds, opcode 2 multiplies, and opcode 99 halts.",
        "The instruction pointer advances by 4 after opcode 1 or 2 and does not advance after halt.",
        "Unknown opcodes should fail loudly in a real interpreter; these app tests use valid programs.",
    ],
    "constraints": ["1 <= program.length <= 10^5", "program contains opcodes 1, 2, and 99 in valid positions"],
    "starter_code": {
        "python": "def run_intcode(program):\n    # Your code here\n    pass",
        "javascript": "function runIntcode(program) {\n    // Your code here\n}",
        "java": "public int[] runIntcode(int[] program) {\n    // Your code here\n    return new int[]{};\n}",
    },
    "boilerplate_code": {
        "python": "# Test runner (read-only)\nif __name__ == \"__main__\":\n    print(run_intcode([1, 0, 0, 0, 99]))",
        "javascript": "// Test runner (read-only)\nconsole.log(runIntcode([1, 0, 0, 0, 99]));",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"program": [1, 0, 0, 0, 99]}, "expected": [2, 0, 0, 0, 99], "description": "Source data 001", "tags": ["basic"]},
        {"input": {"program": [2, 3, 0, 3, 99]}, "expected": [2, 3, 0, 6, 99], "description": "Multiplication", "tags": ["basic"]},
        {"input": {"program": [2, 4, 4, 5, 99, 0]}, "expected": [2, 4, 4, 5, 99, 9801], "description": "Store near end", "tags": ["basic"]},
        {"input": {"program": [1, 1, 1, 4, 99, 5, 6, 0, 99]}, "expected": [30, 1, 1, 4, 2, 5, 6, 0, 99], "description": "Multiple instructions", "tags": ["tricky"]},
        {"input": {"program": [1, 9, 10, 3, 2, 3, 11, 0, 99, 30, 40, 50]}, "expected": [3500, 9, 10, 70, 2, 3, 11, 0, 99, 30, 40, 50], "description": "Canonical full example", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Instruction Pointer Simulation",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": "Copy memory, then step through opcodes until the halt instruction appears.",
            "code": {
                "python": (
                    "def run_intcode(program):\n"
                    "    memory = program[:]\n"
                    "    ip = 0\n"
                    "    while memory[ip] != 99:\n"
                    "        opcode, a, b, dest = memory[ip:ip + 4]\n"
                    "        if opcode == 1:\n"
                    "            memory[dest] = memory[a] + memory[b]\n"
                    "        elif opcode == 2:\n"
                    "            memory[dest] = memory[a] * memory[b]\n"
                    "        else:\n"
                    "            raise ValueError(f'unknown opcode {opcode}')\n"
                    "        ip += 4\n"
                    "    return memory"
                ),
                "javascript": (
                    "function runIntcode(program) {\n"
                    "    const memory = [...program];\n"
                    "    for (let ip = 0; memory[ip] !== 99; ip += 4) {\n"
                    "        const [opcode, a, b, dest] = memory.slice(ip, ip + 4);\n"
                    "        if (opcode === 1) memory[dest] = memory[a] + memory[b];\n"
                    "        else if (opcode === 2) memory[dest] = memory[a] * memory[b];\n"
                    "        else throw new Error(`unknown opcode ${opcode}`);\n"
                    "    }\n"
                    "    return memory;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Describe memory as a mutable array and clone it before running instructions.",
        "2. Read `memory[ip]` as the opcode. Stop immediately on 99.",
        "3. For opcodes 1 and 2, read `a`, `b`, and `dest` from the next three cells and treat them as addresses.",
        "4. Write addition or multiplication into `memory[dest]`.",
        "5. Move `ip` by four and repeat until halt.",
    ],
    "tips": [
        "The parameters are addresses. Reading them as raw values produces plausible but wrong answers.",
        "The example `[1, 0, 0, 0, 99]` is the fastest way to check address-based writes.",
        "Keep interpreter dispatch explicit. A small `if/elif` is easier to audit than clever arithmetic here.",
        "A natural follow-up is adding parameter modes, input/output opcodes, or finding noun/verb values.",
    ],
    "companies": [],
    "topics": ["Array", "Simulation", "Interpreter"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(program):
    memory = program[:]
    ip = 0
    while memory[ip] != 99:
        opcode, a, b, dest = memory[ip:ip + 4]
        if opcode == 1:
            memory[dest] = memory[a] + memory[b]
        elif opcode == 2:
            memory[dest] = memory[a] * memory[b]
        else:
            raise ValueError(f"unknown opcode {opcode}")
        ip += 4
    return memory


register(PAYLOAD, REFERENCE)
