"""Rocket Equation Fuel Sum — Easy. Array, Math.

A one-pass map-and-sum that applies the floor-division fuel formula
to each module mass. The trick is integer division — floating-point
rounding produces wrong answers on the Advent of Code test vectors.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Rocket Equation Fuel Sum",
    "difficulty": "Easy",
    "description": (
        "Given module masses, compute total fuel. Fuel for one mass is `floor(mass / 3) - 2`.\n\n"
        "Examples: mass `12` needs `2` fuel, `14` needs `2`, `1969` needs `654`, and `100756` needs `33583`."
    ),
    "hints": [
        "Transform each mass independently, then sum the results.",
        "Use integer division, not floating-point rounding. In Python, `mass // 3 - 2` matches the rule.",
        "This is part 1: do not include fuel for the added fuel yet.",
        "Small masses can produce zero or negative values; follow the stated formula for each input case.",
    ],
    "constraints": ["0 <= masses.length <= 10^5", "0 <= masses[i] <= 10^9"],
    "starter_code": {
        "python": "def rocket_fuel_sum(masses):\n    # Your code here\n    pass",
        "javascript": "function rocketFuelSum(masses) {\n    // Your code here\n}",
        "java": "public int rocketFuelSum(int[] masses) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": "# Test runner (read-only)\nif __name__ == \"__main__\":\n    print(rocket_fuel_sum([12, 14, 1969]))",
        "javascript": "// Test runner (read-only)\nconsole.log(rocketFuelSum([12, 14, 1969]));",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"masses": [12]}, "expected": 2, "description": "Source data 001", "tags": ["basic"]},
        {"input": {"masses": [14]}, "expected": 2, "description": "Source example", "tags": ["basic"]},
        {"input": {"masses": [1969]}, "expected": 654, "description": "Large example", "tags": ["basic"]},
        {"input": {"masses": [100756]}, "expected": 33583, "description": "Largest source example", "tags": ["basic"]},
        {"input": {"masses": [12, 14, 1969, 100756]}, "expected": 34241, "description": "Multiple modules", "tags": ["edge"]},
        {"input": {"masses": []}, "expected": 0, "description": "No modules", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Map and Sum",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": "Apply the fuel formula to every mass and keep a running total.",
            "code": {
                "python": "def rocket_fuel_sum(masses):\n    return sum(m // 3 - 2 for m in masses)",
                "javascript": "function rocketFuelSum(masses) {\n    return masses.reduce((sum, m) => sum + Math.floor(m / 3) - 2, 0);\n}",
            },
        },
    ],
    "thought_process": [
        "1. Restate the formula and confirm the input is a list of module masses, not a raw newline-separated file.",
        "2. Apply integer division and subtraction to one mass first.",
        "3. Map that helper across all masses and keep a running sum.",
        "4. Explicitly separate this part from the recursive fuel-mass variant.",
    ],
    "tips": [
        "Part 1 is intentionally linear; do not recurse on the fuel mass.",
        "Avoid `round(mass / 3)`: the puzzle requires floor division.",
        "If adapting from the original Advent of Code prompt, parse input outside the solution and keep this function focused on computation.",
    ],
    "companies": [],
    "topics": ["Array", "Math"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(masses):
    return sum(m // 3 - 2 for m in masses)


register(PAYLOAD, REFERENCE)
