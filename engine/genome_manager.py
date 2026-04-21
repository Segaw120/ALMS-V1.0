class GenomeManager:
    """
    Manages the User's baseline intelligence vectors and extrapolates 
    the mathematical 'Superman' alignment mapping over time.
    """
    def __init__(self):
        self.user_base_vector = {}
        self.superman_vector = {}
        self.onboarding_questions = [
            "Are you primarily motivated by structural defense or chaotic expansion?",
            "When faced with a collapsing schedule, do you default to discarding non-essentials or compressing timeframes?",
            "Map your tolerance for high-variance financial outcomes over a 5-year horizon (1-10 scale).",
            "What happens if your primary venture completely flatlines tomorrow? How does your strategy pivot instantly?",
            "Do you consider logic an iterative tool or a final axiom?"
        ]

    def input_onboarding_answers(self, answers_dict: dict):
        """Converts raw onboarding text into algorithmic genome properties."""
        # Initial Defaults
        risk_tolerance = 0.5
        speed_vs_structure = 0.5

        # Mock Quantization logic: Analysing keywords in the full answer set
        all_text = " ".join(answers_dict.values()).lower()
        
        if "expansion" in all_text or "chaotic" in all_text:
            speed_vs_structure += 0.2
        if "structural" in all_text or "defense" in all_text:
            speed_vs_structure -= 0.2
            
        if "high-variance" in all_text or "10" in all_text:
            risk_tolerance += 0.3
        if "compressing" in all_text:
            speed_vs_structure += 0.1
        if "discarding" in all_text:
            speed_vs_structure -= 0.1

        self.user_base_vector = {
            "risk_tolerance": max(0.0, min(1.0, risk_tolerance)),
            "speed_vs_structure": max(0.0, min(1.0, speed_vs_structure)),
            "fractal_divergence_cap": 3,
            "biological_anchors": answers_dict
        }
        self._recalculate_superman_vector()


    def _recalculate_superman_vector(self):
        """
        Takes the user_base_vector and applies the Übermensch mathematical skew:
        Removing biological exhaustion penalties, maxing structural fortitude limits.
        """
        self.superman_vector = self.user_base_vector.copy()
        
        # Scaling logic defined directly in instructions.md
        self.superman_vector["biological_exhaustion_penalty"] = 0.0
        self.superman_vector["risk_tolerance"] = min(1.0, self.superman_vector.get("risk_tolerance", 0.5) * 1.5)
        self.superman_vector["fractal_divergence_cap"] = 100 # Near infinite reasoning chains simulated
        self.superman_vector["status"] = "EMERGENT_OPTIMIZED"

    def apply_venture_feedback(self, insights: dict):
        """Called daily when new insights are imported by the user."""
        # Modifies base vector gracefully.
        for key, shift in insights.items():
            if key in self.user_base_vector and isinstance(self.user_base_vector[key], (int, float)):
                self.user_base_vector[key] += shift
        self._recalculate_superman_vector()
