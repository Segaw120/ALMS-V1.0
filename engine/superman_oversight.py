import logging
from core_engine.genome_manager import GenomeManager
from core_engine.world_model import WorldModelMemory

class SupermanOversight:
    def __init__(self, genome_manager: GenomeManager, world_model: WorldModelMemory):
        self.genome_manager = genome_manager
        self.world_model = world_model

    def evaluate_simulations(self, simulation_outcomes: list[dict]):
        """
        Ranks simulation outcomes dynamically based on the user's updated Genome configurations.
        """
        sv = self.genome_manager.superman_vector
        if not sv:
            logging.warning("Superman vector not yet initialised. Using default ranking.")
            sv = {"risk_tolerance": 0.5, "speed_vs_structure": 0.5}

        ranked_outcomes = []
        for outcome in simulation_outcomes:
            # 1.0 risk tolerance means high risk gets higher score
            risk_score = outcome.get('risk', 0.5) * sv.get('risk_tolerance', 0.5) 
            # 1.0 speed vs structure means speed gets higher score, else structure
            speed_score = outcome.get('speed', 0.5) * sv.get('speed_vs_structure', 0.5)
            structure_score = outcome.get('structural_integrity', 0.5) * (1.0 - sv.get('speed_vs_structure', 0.5))
            
            total_score = outcome.get('reward', 0) + risk_score + speed_score + structure_score
            ranked_outcomes.append({
                "outcome_data": outcome,
                "superman_score": total_score
            })
            
        ranked_outcomes.sort(key=lambda x: x["superman_score"], reverse=True)
        return ranked_outcomes

    def generate_daily_synthesis(self):
        """
        Finalises the daily reporting dashboard loop, formatting everything 
        into synthesized outputs for the user's morning review. Returns rich Markdown.
        """
        all_lessons = self.world_model.fetch_all_lessons()
        
        simulated_outcomes = []
        for lesson in all_lessons:
            simulated_outcomes.append({
                "id": lesson[0],
                "industry": lesson[1],
                "action": lesson[3],
                "outcome_desc": lesson[4],
                "reward": lesson[5],
                "risk": 0.8 if "High" in lesson[3] else 0.4, 
                "speed": 0.9 if "Fast" in lesson[3] else 0.5,
                "structural_integrity": 0.3 if "Fast" in lesson[3] else 0.8
            })

        ranked = self.evaluate_simulations(simulated_outcomes)

        sv = self.genome_manager.superman_vector
        if not sv:
            sv = {"risk_tolerance": 0.5, "speed_vs_structure": 0.5, "biological_exhaustion_penalty": 0.1}

        # Calculate total score for capital allocation pooling
        total_score_pool = sum([max(0, item["superman_score"]) for item in ranked[:5]])
        total_simulated_capital = 100000  # e.g., $100k allocation pool

        synthesis = "## 📊 Daily Superman Synthesis\n\n"
        synthesis += "### 🧬 Active Genome Alignment\n"
        synthesis += f"- **Risk Tolerance:** `{sv.get('risk_tolerance', 'N/A')}`\n"
        synthesis += f"- **Core Strategy:** `{'Expansive' if sv.get('speed_vs_structure', 0.5) > 0.5 else 'Structural Defense'}`\n"
        synthesis += f"- **Bio Penalty:** `{sv.get('biological_exhaustion_penalty', 'N/A')}`\n\n"
        
        synthesis += "### 🏆 Ranked Simulation Outcomes (Investor Override)\n"
        
        if not ranked:
            synthesis += "> No major simulation outcomes to rank today.\n"
        else:
            synthesis += "| Rank | Industry | Action Taken | Consequence | Alignment | Win Prob. | Cap. Allocation |\n"
            synthesis += "|:---|:---|:---|:---|:---:|:---:|:---:|\n"
            
            top_outcomes = ranked[:5]
            for idx, item in enumerate(top_outcomes):
                data = item["outcome_data"]
                # Mock win probability using logistic squashing or simple scaling
                win_prob = min(99.9, max(1.0, (item["superman_score"] / 2.0) * 100))
                
                # Capital allocation weighted by score
                capital = 0
                if total_score_pool > 0 and item["superman_score"] > 0:
                    capital = int((item["superman_score"] / total_score_pool) * total_simulated_capital)

                industry = data.get("industry", "Unknown")
                action = data.get("action", "N/A")
                outcome_desc = data.get("outcome_desc", "N/A")
                alignment = f"{item['superman_score']:.2f}"
                prob_str = f"{win_prob:.1f}%"
                cap_str = f"${capital:,}"

                synthesis += f"| **{idx+1}** | {industry} | {action} | {outcome_desc} | {alignment} | {prob_str} | **{cap_str}** |\n"
            
            # Actionable Tactics
            synthesis += "\n### ⚡ Actionable Tactics\n"
            best = top_outcomes[0]["outcome_data"]
            synthesis += f"1. **Deploy Capital to [{best.get('industry', 'Primary')}]**: The simulation definitively shows that executing `{best.get('action', 'the primary action')}` yields optimal alignment with your current risk profile.\n"
            synthesis += f"2. **Monitor Volatility**: Expect `{best.get('outcome_desc', 'some turbulence')}`. Setup automated stop-losses dynamically based on the Thought Lab's threshold variables.\n"
            
            synthesis += "\n```mermaid\ngraph TD\n"
            synthesis += f"    A[Superman Genome] -->|Capital Allocation| B[{best.get('industry', 'Test Lab')}]\n"
            synthesis += f"    B --> C({best.get('action', 'Action')})\n"
            synthesis += f"    C --> D[{best.get('outcome_desc', 'Outcome')}]\n"
            synthesis += "```\n"

        return synthesis
