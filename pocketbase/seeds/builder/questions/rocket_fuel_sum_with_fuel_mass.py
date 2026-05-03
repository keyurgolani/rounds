"""Rocket Equation Fuel Sum With Fuel Mass — Easy. Array, Math, Simulation.

The recursive-fuel variant: each module's fuel itself needs fuel, so
iterate the floor-division formula until it stops producing positive
values. The common bug is adding the final negative term.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Rocket Equation Fuel Sum With Fuel Mass",
    "difficulty": "Easy",
    "description": (
        "Given module masses, compute total fuel while also accounting for the fuel required by the added fuel. "
        "For each mass, repeatedly apply `floor(mass / 3) - 2` until the next value is zero or negative.\n\n"
        "Example: mass `1969` needs `654 + 216 + 70 + 21 + 5 = 966`."
    ),
    "hints": [
        "Write a helper for one mass first, then sum that helper over all modules.",
        "Each loop step uses the previous fuel value as the next mass.",
        "Add a fuel value only if it is positive; stop when the formula returns zero or less.",
        "This can be iterative or recursive, but iteration avoids recursion-depth concerns for large masses.",
    ],
    "constraints": ["0 <= masses.length <= 10^5", "0 <= masses[i] <= 10^9"],
    "starter_code": {
        "python": "def rocket_fuel_sum_with_fuel_mass(masses):\n    # Your code here\n    pass",
        "javascript": "function rocketFuelSumWithFuelMass(masses) {\n    // Your code here\n}",
        "java": "public int rocketFuelSumWithFuelMass(int[] masses) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": "# Test runner (read-only)\nif __name__ == \"__main__\":\n    print(rocket_fuel_sum_with_fuel_mass([14, 1969]))",
        "javascript": "// Test runner (read-only)\nconsole.log(rocketFuelSumWithFuelMass([14, 1969]));",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"masses": [14]}, "expected": 2, "description": "Source data 001", "tags": ["basic"]},
        {"input": {"masses": [1969]}, "expected": 966, "description": "Recursive source example", "tags": ["basic"]},
        {"input": {"masses": [100756]}, "expected": 50346, "description": "Large recursive example", "tags": ["basic"]},
        {"input": {"masses": [14, 1969, 100756]}, "expected": 51314, "description": "Multiple modules", "tags": ["edge"]},
        {"input": {"masses": [1, 2, 6]}, "expected": 0, "description": "No positive fuel", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Iterative Fuel Accumulation",
            "time_complexity": "O(n log M)",
            "space_complexity": "O(1)",
            "description": "For each mass, repeatedly convert the current mass into fuel until the formula stops producing positive fuel.",
            "code": {
                "python": (
                    "def rocket_fuel_sum_with_fuel_mass(masses):\n"
                    "    total = 0\n"
                    "    for mass in masses:\n"
                    "        fuel = mass // 3 - 2\n"
                    "        while fuel > 0:\n"
                    "            total += fuel\n"
                    "            fuel = fuel // 3 - 2\n"
                    "    return total"
                ),
                "javascript": (
                    "function rocketFuelSumWithFuelMass(masses) {\n"
                    "    let total = 0;\n"
                    "    for (const mass of masses) {\n"
                    "        let fuel = Math.floor(mass / 3) - 2;\n"
                    "        while (fuel > 0) {\n"
                    "            total += fuel;\n"
                    "            fuel = Math.floor(fuel / 3) - 2;\n"
                    "        }\n"
                    "    }\n"
                    "    return total;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Solve one mass before thinking about the full list.",
        "2. Compute the next fuel value, check if it is positive, then add it.",
        "3. Feed that fuel value back into the formula until the sequence ends.",
        "4. Sum each module's recursive fuel total in the outer loop.",
    ],
    "tips": [
        "The common bug is adding the final negative fuel value; guard before adding.",
        "Use `14 -> 2`, `1969 -> 966`, and `100756 -> 50346` as quick sanity checks.",
        "Do not mutate the `masses` array; the recurrence only needs a local `fuel` variable.",
    ],
    "companies": [],
    "topics": ["Array", "Math", "Simulation"],
    "time_complexity": "O(n log M)",
    "space_complexity": "O(1)",
}


def REFERENCE(masses):
    total = 0
    for mass in masses:
        fuel = mass // 3 - 2
        while fuel > 0:
            total += fuel
            fuel = fuel // 3 - 2
    return total


register(PAYLOAD, REFERENCE)
