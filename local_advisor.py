"""
Local Finance Advisor Model (Offline AI Engine)
-----------------------------------------------
A self-contained, offline financial intelligence and reasoning model that runs
locally out of the box without requiring any external cloud APIs or API keys.

It performs:
1. Multi-metric financial risk and health assessment (50/30/20, burn rate, runway).
2. Persona classification (Freelancer, Student, Household Manager, Salaried Professional).
3. Goal velocity and horizon forecasting.
4. Natural Language Advisory Generation tailored to individual spending behavior.
"""

from typing import Dict, List, Optional


class LocalFinanceAdvisorModel:
    def __init__(self):
        self.model_name = "Local Advisor AI (Offline Model)"
        self.version = "1.2.0"

    def analyze(
        self,
        income: float,
        total_expenses: float,
        category_breakdown: Dict[str, float],
        income_sources: Optional[List[Dict]] = None,
        goals: Optional[List] = None,
    ) -> List[str]:
        """
        Executes local quantitative analysis and generates tailored, natural-language
        financial recommendations.
        """
        insights: List[str] = []

        # 0. Zero-Income Baseline Check
        if income <= 0:
            return [
                "[Baseline Required] No monthly income has been logged yet. Record your primary revenue or allowance to initiate budget analysis.",
                "[Cashflow Strategy] Log all irregular income sources or side gigs to accurately compute your baseline burn rate.",
            ]

        net_savings = income - total_expenses
        savings_rate = (net_savings / income) * 100
        monthly_burn = total_expenses if total_expenses > 0 else 1.0

        # 1. Detect User Persona
        persona = self._detect_persona(income, category_breakdown, income_sources)

        # 2. Macro Savings & Cashflow Assessment
        if net_savings < 0:
            deficit = abs(net_savings)
            insights.append(
                f"[Deficit Alert - {persona}] You are running a monthly deficit of ${deficit:.2f} "
                f"({abs(savings_rate):.1f}% over income). Immediate cost containment is recommended "
                f"to prevent debt accumulation."
            )
        elif savings_rate < 15:
            target_cut = (0.20 * income) - net_savings
            insights.append(
                f"[Savings Pace - {persona}] Current savings rate is {savings_rate:.1f}%. "
                f"To reach the healthy 20% benchmark, aim to optimize roughly ${max(0.0, target_cut):.2f} "
                f"from discretionary spending this month."
            )
        elif savings_rate < 30:
            insights.append(
                f"[Balanced Budget - {persona}] Strong financial health with a {savings_rate:.1f}% savings rate "
                f"(${net_savings:.2f} saved). Your core income comfortably covers expenses."
            )
        else:
            insights.append(
                f"[High Capital Efficiency - {persona}] Outstanding performance with a {savings_rate:.1f}% savings rate! "
                f"Consider directing surplus capital toward high-yield savings or investment allocations."
            )

        # 3. Category Anomaly & 50/30/20 Structural Analysis
        category_insights = self._analyze_categories(income, category_breakdown, persona)
        if category_insights:
            insights.extend(category_insights)

        # 4. Goal Completion Forecasting & Runway Guidance
        goal_insights = self._analyze_goals(net_savings, goals, monthly_burn)
        if goal_insights:
            insights.extend(goal_insights)

        # 5. Persona-Specific Strategic Advisory
        persona_advice = self._get_persona_strategy(persona, income, income_sources, net_savings)
        if persona_advice:
            insights.append(persona_advice)

        # Ensure we return the most relevant 4 actionable bullet points
        return insights[:4]

    def _detect_persona(
        self,
        income: float,
        categories: Dict[str, float],
        income_sources: Optional[List[Dict]] = None,
    ) -> str:
        """Classifies financial persona based on income distribution and spending categories."""
        # Check for Freelancer / Variable Income
        if income_sources and len(income_sources) > 1:
            sources_text = " ".join(s.get("source", "").lower() for s in income_sources)
            if any(k in sources_text for k in ["client", "freelance", "contract", "project", "gig"]):
                return "Freelancer / Variable Income"

        # Check for Household Manager
        household_categories = [c.lower() for c in categories.keys()]
        if any(h in household_categories for h in ["groceries", "utilities", "healthcare", "education"]) and len(categories) >= 3:
            return "Household Manager"

        # Check for Constrained Budget / Student
        if income < 1800 and any(c.lower() in ["education", "books", "tuition"] for c in categories.keys()):
            return "Student / Limited Budget"

        return "Salaried Professional"

    def _analyze_categories(
        self, income: float, categories: Dict[str, float], persona: str
    ) -> List[str]:
        """Scans expense categories against standard economic thresholds."""
        findings = []

        # Rent / Housing analysis (guideline <= 30-35%)
        for cat, amt in categories.items():
            pct = (amt / income) * 100
            c_low = cat.lower()

            if "rent" in c_low or "housing" in c_low:
                if pct > 35:
                    findings.append(
                        f"[Housing Over-Weight] Housing consumes {pct:.1f}% of your monthly income "
                        f"(recommended: <= 30%). Exploring utility savings or rent stabilization could relieve cash pressure."
                    )
            elif "food" in c_low or "groceries" in c_low:
                if pct > 25:
                    findings.append(
                        f"[Food & Dining] Food spending is at {pct:.1f}% (${amt:.2f}). "
                        f"Reducing takeout frequency or weekly meal-batching could save an estimated ${amt * 0.15:.2f}/mo."
                    )
            elif "entertainment" in c_low or "leisure" in c_low:
                if pct > 15:
                    findings.append(
                        f"[Discretionary Spending] Entertainment represents {pct:.1f}% of your budget. "
                        f"Auditing subscription services and dining out can quickly recapture ${amt * 0.20:.2f}."
                    )
            elif "transport" in c_low:
                if pct > 18:
                    findings.append(
                        f"[Commute Optimization] Transport costs are {pct:.1f}% of income. "
                        f"Consider pass discounts or transit alternatives."
                    )

        return findings

    def _analyze_goals(
        self, net_savings: float, goals: Optional[List], monthly_burn: float
    ) -> List[str]:
        """Forecasts goal timelines and emergency buffer sufficiency."""
        findings = []
        if not goals:
            target_buffer = monthly_burn * 3
            findings.append(
                f"[Emergency Buffer Recommendation] No active savings goals found. "
                f"We recommend setting a 3-month Emergency Fund target of ${target_buffer:.2f} to absorb unexpected expenses."
            )
            return findings

        # Pick the most urgent incomplete goal
        incomplete_goals = [g for g in goals if g.current_amount < g.target_amount]
        if incomplete_goals:
            primary_goal = incomplete_goals[0]
            remaining = primary_goal.target_amount - primary_goal.current_amount

            if net_savings > 0:
                months_needed = remaining / net_savings
                if months_needed <= 1.0:
                    findings.append(
                        f"[Goal Milestone Ahead] Your '{primary_goal.name}' goal has ${remaining:.2f} left. "
                        f"At your current monthly savings, you are projected to complete it this month!"
                    )
                else:
                    findings.append(
                        f"[Goal Horizon] At your current savings rate, '{primary_goal.name}' "
                        f"(${remaining:.2f} remaining) is on track to be reached in ~{months_needed:.1f} months."
                    )
            else:
                findings.append(
                    f"[Goal Warning] Goal '{primary_goal.name}' requires ${remaining:.2f}. "
                    f"Allocate a fixed portion of income on payday before discretionary spending."
                )

        return findings

    def _get_persona_strategy(
        self, persona: str, income: float, income_sources: Optional[List[Dict]], net_savings: float
    ) -> str:
        """Generates strategic guidance tailored to the user's specific lifestyle persona."""
        if persona == "Freelancer / Variable Income":
            return (
                "[Freelancer Buffer Rule] Because contract earnings fluctuate, maintain a separate "
                "3-to-6 month buffer account and set aside 25-30% of each invoice for quarterly taxes."
            )
        elif persona == "Student / Limited Budget":
            return (
                "[Student Smart Saving] Prioritize student discounts on software, transit, and textbooks. "
                "Even saving $25 to $50 consistently each month builds long-term compounding discipline."
            )
        elif persona == "Household Manager":
            return (
                "[Family Resource Allocation] Review recurring utility providers and consider "
                "household wholesale purchases to lower per-unit consumable costs by 10-18%."
            )
        else:
            return (
                "[Wealth Building] Automate an electronic transfer of your net savings to a separate account "
                "immediately on payday (the 'Pay Yourself First' principle)."
            )


# Singleton instance ready to run out-of-the-box
local_model = LocalFinanceAdvisorModel()

