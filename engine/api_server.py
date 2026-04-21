from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from fpdf import FPDF
from core_engine.genome_manager import GenomeManager
from core_engine.llm_manager import LLMManager
from core_engine.world_model import WorldModelMemory
from core_engine.superman_oversight import SupermanOversight
from core_engine.logic_validator import LogicValidator
from core_engine.fractal_reasoner import FractalReasoner
from core_engine.obsidian_bridge import ObsidianBridge
from core_engine.memory_manager import MemoryManager
from core_engine.auto_researcher import AutoResearcher
from core_engine.graph_analyzer import GraphAnalyzer
from core_engine.prompt_compressor import PromptCompressor
from core_engine.deep_solver import DeepSolver
import os
import json

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/genome")
async def get_genome():
    return {
        "user_base": genome_manager.user_base_vector,
        "superman": genome_manager.superman_vector
    }

@app.get("/api/vault/stats")
async def get_vault_stats():
    neurons = memory.compressor.load_neurons()
    return {
        "neuron_count": len(neurons),
        "top_neurons": sorted(neurons.keys(), key=lambda k: len(neurons[k].get("synapses", {})), reverse=True)[:10]
    }

@app.get("/api/traces")
async def get_traces():
    traces = []
    for f in os.listdir(vault_path):
        if f.startswith("TRACE-") and f.endswith(".md"):
            content = obsidian.read_node(f.replace(".md", ""))
            # Extract query from content
            match = re.search(r"\*\*Original Query:\*\* (.*)", content)
            query = match.group(1) if match else "Unknown Query"
            traces.append({
                "id": f.replace(".md", ""),
                "query": query,
                "timestamp": f.replace("TRACE-", "").replace(".md", "") # Mock timestamp from ID for now
            })
    return traces[::-1] # Newest first

@app.get("/api/system/health")
async def get_system_health():
    """Returns a sanitized system health check."""
    neurons = memory.compressor.load_neurons()
    ollama_ok = False
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=2)
        ollama_ok = r.status_code == 200
    except Exception:
        pass
    return {
        "status": "online",
        "ollama": ollama_ok,
        "neuron_count": len(neurons),
        "genome_active": bool(genome_manager.user_base_vector),
    }

@app.get("/api/active-tasks")
async def get_active_tasks():
    """Returns all currently active DeepSolve tasks."""
    return [
        {"task_id": tid, **info}
        for tid, info in deep_solver.active_tasks.items()
    ]

@app.get("/api/research/experiments")
async def get_experiments():
    """Returns all EXP nodes from the vault with metadata."""
    results = []
    for f in os.listdir(vault_path):
        if f.startswith("EXP-") and f.endswith(".md"):
            node_id = f.replace(".md", "")
            content = obsidian.read_node(node_id)
            hypo_m   = re.search(r'\*\*Hypothesis target:\*\* \[\[(.*?)\]\]', content)
            status_m = re.search(r'\*\*Status:\*\* (.*)', content)
            result_m = re.search(r'```text\n(.*?)\n```', content, re.DOTALL)
            double_m = re.search(r'# Double-Blind Confirmed\n(\w+)', content)
            results.append({
                "id":              node_id,
                "hypothesis":      hypo_m.group(1)   if hypo_m   else "",
                "status":          status_m.group(1) if status_m else "",
                "results_summary": result_m.group(1)[:400] if result_m else "",
                "double_blind":    double_m and double_m.group(1).lower() == "true",
                "linked_task":     re.search(r'trace/(SOLVE-\w+)', content) and re.search(r'trace/(SOLVE-\w+)', content).group(1),
            })
    return sorted(results, key=lambda x: x["id"], reverse=True)

@app.get("/api/vault/search")
async def search_vault(q: str = ""):
    """Fuzzy search over all vault node filenames and content snippets."""
    if not q:
        return []
    q_lower = q.lower()
    results = []
    for f in os.listdir(vault_path):
        if not f.endswith(".md"): continue
        node_id = f.replace(".md", "")
        if q_lower in node_id.lower():
            results.append({"id": node_id, "snippet": None, "node_type": ""})
            continue
        try:
            content = obsidian.read_node(node_id)
            idx = content.lower().find(q_lower)
            if idx >= 0:
                snippet = content[max(0, idx-60):idx+120].replace("\n", " ")
                type_m  = re.search(r'node_type: (\w+)', content)
                results.append({
                    "id":        node_id,
                    "snippet":   snippet,
                    "node_type": type_m.group(1) if type_m else "",
                })
        except Exception:
            pass
    return results[:40]

@app.get("/api/vault/node/{node_id}")
async def get_vault_node(node_id: str):
    """Returns the full markdown content of a vault node."""
    try:
        content = obsidian.read_node(node_id)
        return {"id": node_id, "content": content}
    except Exception as e:
        return {"id": node_id, "content": f"Node not found: {str(e)}"}


# ── ORG / SYS File CRUD ──────────────────────────────────────────────────

class OrgUpdate(BaseModel):
    content: str
    status: str = "active"
    tags: list[str] = []

class OrgCreate(BaseModel):
    id: str
    title: str
    type: str = "system_axiom"
    status: str = "active"
    tags: list[str] = []
    content: str

@app.get("/api/org")
async def list_org_files():
    """Returns all SYS-prefixed files (ORG type) from the vault."""
    items = []
    for f in sorted(os.listdir(vault_path)):
        if f.startswith("SYS-") and f.endswith(".md"):
            node_id = f.replace(".md", "")
            raw = obsidian.read_node(node_id) or ""
            # Extract frontmatter fields
            title_m  = re.search(r'^# (.+)$', raw, re.MULTILINE)
            type_m   = re.search(r'^type: (.+)$', raw, re.MULTILINE)
            status_m = re.search(r'^status: (.+)$', raw, re.MULTILINE)
            tags_raw = re.findall(r'^  - (.+)$', raw[raw.find('tags:'):raw.find('---', raw.find('tags:'))], re.MULTILINE) if 'tags:' in raw else []
            items.append({
                "id":     node_id,
                "title":  title_m.group(1).strip()  if title_m  else node_id,
                "type":   type_m.group(1).strip()   if type_m   else "",
                "status": status_m.group(1).strip() if status_m else "",
                "tags":   tags_raw,
            })
    return items

@app.get("/api/org/{node_id}")
async def get_org_file(node_id: str):
    """Returns the full content of a single SYS file."""
    raw = obsidian.read_node(node_id)
    if not raw:
        return {"error": "Not found"}
    # Strip YAML frontmatter — return body only for editing
    body = re.sub(r'^---.*?---\n', '', raw, flags=re.DOTALL).strip()
    title_m  = re.search(r'^# (.+)$', raw, re.MULTILINE)
    type_m   = re.search(r'^type: (.+)$', raw, re.MULTILINE)
    status_m = re.search(r'^status: (.+)$', raw, re.MULTILINE)
    tags_raw = re.findall(r'^  - (.+)$', raw[raw.find('tags:'):raw.find('---', raw.find('tags:'))], re.MULTILINE) if 'tags:' in raw else []
    return {
        "id":      node_id,
        "title":   title_m.group(1).strip()  if title_m  else node_id,
        "type":    type_m.group(1).strip()   if type_m   else "",
        "status":  status_m.group(1).strip() if status_m else "",
        "tags":    tags_raw,
        "body":    body,
        "raw":     raw,
    }

@app.put("/api/org/{node_id}")
async def update_org_file(node_id: str, update: OrgUpdate):
    """Overwrites the body and metadata of an existing SYS file."""
    obsidian.write_node(
        node_id    = node_id,
        tags       = update.tags,
        parent_nodes = ["SYS-001"],
        content    = update.content,
        node_type  = "system_axiom",
        metadata   = {"status": update.status},
    )
    return {"ok": True, "id": node_id}

@app.post("/api/org")
async def create_org_file(org: OrgCreate):
    """Creates a new SYS file from scratch."""
    node_id = org.id if org.id.startswith("SYS-") else f"SYS-{org.id}"
    full_content = f"# {org.title}\n\n{org.content}"
    obsidian.write_node(
        node_id    = node_id,
        tags       = org.tags,
        parent_nodes = ["SYS-001"],
        content    = full_content,
        node_type  = org.type,
        metadata   = {"status": org.status},
    )
    return {"ok": True, "id": node_id}

@app.delete("/api/org/{node_id}")
async def delete_org_file(node_id: str):
    """Permanently deletes a SYS file from the vault. Irreversible."""
    file_path = os.path.join(vault_path, f"{node_id}.md")
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"ok": True}
    return {"ok": False, "error": "File not found"}

@app.get("/api/export/pdf")
async def export_vault_pdf():
    """Generates a sequential PDF of all system axioms, reasoning traces, and experiments."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Title Page
    pdf.set_font("helvetica", "B", 24)
    pdf.cell(0, 40, "Personal OS: Intelligence Audit", ln=True, align="C")
    pdf.set_font("helvetica", "I", 12)
    pdf.cell(0, 10, f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.ln(20)
    
    def add_node_to_pdf(node_id, title_prefix=""):
        content = obsidian.read_node(node_id)
        if not content: return
        
        # Strip frontmatter
        body = re.sub(r'^---.*?---\n', '', content, flags=re.DOTALL).strip()
        
        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(59, 130, 246) # Blue
        pdf.cell(0, 10, f"{title_prefix}{node_id}", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
        
        pdf.set_font("helvetica", "", 10)
        # Simple markdown to plain text conversion for PDF
        body = body.replace("**", "").replace("__", "")
        # Remove mermaid blocks
        body = re.sub(r'```mermaid.*?```', '[Diagram omitted]', body, flags=re.DOTALL)
        # Remove code blocks
        body = body.replace("```", "")
        
        pdf.multi_cell(0, 5, body)
        pdf.ln(10)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

    # 1. System Core (SYS)
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 15, "Phase 1: System Axioms & Configuration", ln=True)
    pdf.ln(5)
    
    sys_files = sorted([f.replace(".md", "") for f in os.listdir(vault_path) if f.startswith("SYS-")])
    for s in sys_files:
        add_node_to_pdf(s)
        
    # 2. Reasoning Traces & Experiments (SOLVE -> EXP)
    pdf.add_page()
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 15, "Phase 2: Reasoning Threads & Empirical Research", ln=True)
    pdf.ln(5)
    
    traces = sorted([f.replace(".md", "") for f in os.listdir(vault_path) if f.startswith("TRACE-")], reverse=True)
    seen_exps = set()
    
    for t in traces:
        add_node_to_pdf(t, "Trace: ")
        
        # Find linked experiments
        links = obsidian.extract_links(t)
        for l in links:
            if l.startswith("EXP-") and l not in seen_exps:
                pdf.set_left_margin(20)
                add_node_to_pdf(l, "Experiment: ")
                pdf.set_left_margin(10)
                seen_exps.add(l)

    # Output as byte stream
    pdf_bytes = pdf.output()
    return Response(content=pdf_bytes, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=Intelligence_Audit_{time.strftime('%Y%m%d')}.pdf"
    })


# Global Instances
genome_manager = GenomeManager()
llm = LLMManager()
world_model = WorldModelMemory()
oversight = SupermanOversight(genome_manager, world_model)
validator = LogicValidator(llm)

# Obsidian & Memory setup
vault_path = os.path.join(os.getcwd(), "Vault")
obsidian = ObsidianBridge(vault_path)
memory = MemoryManager(vault_path=vault_path)
researcher = AutoResearcher(llm, obsidian, validator)
prompt_compressor = PromptCompressor(
    vault_path = vault_path,
    obsidian   = obsidian,
    researcher = researcher,   # enables inline AutoResearch on gaps
)

fractal_engine = FractalReasoner(llm, obsidian, memory, validator, researcher)
graph_analyzer = GraphAnalyzer(llm, obsidian, validator)
deep_solver = DeepSolver(llm, obsidian, memory, validator, researcher)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        # tracks {websocket: {"q_index": 0, "answers": {}}}
        self.user_onboarding_states = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Initialize onboarding state if genome is empty
        if not genome_manager.user_base_vector:
            self.user_onboarding_states[websocket] = {"q_index": 0, "answers": {}}
            await self.send_personal_message("System Online. Initializing Genome...", websocket)
            await self.send_personal_message(f"Q1: {genome_manager.onboarding_questions[0]}", websocket)
        else:
            await self.send_personal_message("System Online. Genome Active. Ready for Sparring.", websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if websocket in self.user_onboarding_states:
            del self.user_onboarding_states[websocket]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            
            # Check if we are in onboarding mode
            state = manager.user_onboarding_states.get(websocket)
            
            if state:
                idx = state["q_index"]
                questions = genome_manager.onboarding_questions
                
                # Store answer
                state["answers"][f"q{idx+1}"] = data
                state["q_index"] += 1
                
                next_idx = state["q_index"]
                if next_idx < len(questions):
                    # Send next question
                    await manager.send_personal_message(f"Q{next_idx+1}: {questions[next_idx]}", websocket)
                else:
                    # Onboarding Complete
                    await manager.send_personal_message("Onboarding complete. Extrapolating User Base and Superman Vectors...", websocket)
                    genome_manager.input_onboarding_answers(state["answers"])
                    del manager.user_onboarding_states[websocket]
                    await manager.send_personal_message("Genome Active. We are deep-linked. You may now spars, or use /scan, /branch, /review.", websocket)
                continue

            # Simple router logic (Active after onboarding)
            if data.startswith("/scan"):
                # Surface status without exposing internal vector names
                risk = genome_manager.superman_vector.get('risk_tolerance', 0)
                bio_excl = genome_manager.superman_vector.get('biological_exhaustion_penalty', 1)
                status = (
                    f"**System Status: Online**\n\n"
                    f"- Genome: Active & calibrated\n"
                    f"- Alignment: {'Optimal' if risk > 0.7 else 'Calibrating'}\n"
                    f"- Biological constraints: {'Excluded' if bio_excl == 0 else 'Partially active'}\n"
                    f"- Vault: Synaptic memory loaded"
                )
                await manager.send_personal_message(status, websocket)
            elif data.startswith("/branch"):
                topic = data.replace("/branch", "").strip()
                if not topic:
                    await manager.send_personal_message("Please provide a topic. e.g. `/branch scale strategies`", websocket)
                else:
                    await manager.send_personal_message(f"Spawning divergent reasoning thread on **{topic}**...", websocket)
            elif data.startswith("/analyze_graph"):
                await manager.send_personal_message("Mapping high-nuance reasoning paths across the knowledge graph...", websocket)
                
                async def run_analysis():
                    try:
                        results = await graph_analyzer.pipe_to_evaluation_pipeline()
                        if not results:
                            await manager.send_personal_message("No high-confidence reasoning paths found above the current threshold.", websocket)
                        for idx, r in enumerate(results):
                            critique = r['validation'].get('critique', '')
                            hypo = r['validation'].get('testable_hypothesis')
                            msg = f"**Path {idx+1}** — Confidence: `{r['nuance_score']:.0%}`\n\n{critique}\n"
                            if hypo:
                                msg += f"\n> Verification queued: *{hypo}*\n"
                            await manager.send_personal_message(msg, websocket)
                    except Exception as e:
                        await manager.send_personal_message("Analysis encountered an error. Check system logs.", websocket)
                        
                asyncio.create_task(run_analysis())
                
            elif data.startswith("/deep"):
                query = data.replace("/deep", "").strip()
                if not query:
                    await manager.send_personal_message("Please provide a question. e.g. `/deep how to optimize drawdown recovery`", websocket)
                else:
                    await manager.send_personal_message(f"🔬 **Deep Solve activated** for:\n> *{query}*\n\nRunning continuous verification loop. Updates will appear in the activity panel.", websocket)
                    async def status_update(msg: str):
                        await manager.send_personal_message(f"[Status] {msg}", websocket)
                    asyncio.create_task(deep_solver.solve_continuously(query, status_callback=status_update))
            elif data.startswith("/review"):
                synthesis = oversight.generate_daily_synthesis()
                await manager.send_personal_message(synthesis, websocket)
            else:
                # Full pipeline — suppress internal step name from user
                await manager.send_personal_message("[Pipeline] Compressing query through vault...", websocket)

                result = await llm.generate_with_vault_context(
                    prompt    = data,
                    compressor= prompt_compressor,
                )

                if result["response"]:
                    # Hallucination Check (Grounding Audit)
                    await manager.send_personal_message("[Pipeline] Auditing response for grounding...", websocket)
                    audit = await validator.hallucination_check(result["response"], result["scaffold"])
                    grounding_score = audit.get("grounding_score", 0.0)

                    # Persist full trace to Obsidian
                    trace_id = await prompt_compressor.persist_trace(
                        trace            = result.get("trace", {"trace_id": "TRACE-unknown", "prompt": data}),
                        llm_response     = result["response"],
                        validation_score = grounding_score,
                    )
                    
                    # Reinforce synapses based on grounding
                    prompt_compressor.reinforce_cluster(result["cluster"], grounding_score)

                    # Build a clean, user-facing footer (no internal IDs or module names)
                    confidence = result['match_score']
                    research_ran = bool(result.get('research_results'))
                    p2p_verified = result.get("trace", {}).get("s6_5_p2p", [{}])[0].get("verified", False)
                    
                    if grounding_score >= 0.8:
                        grounding_label = "Fully Grounded"
                    elif grounding_score >= 0.5:
                        grounding_label = "Partially Grounded"
                    else:
                        grounding_label = "Exploratory / Ungrounded"

                    footer = f"\n\n---\n*Status: {grounding_label}*"
                    if p2p_verified:
                        footer += " · **BiltP2P Verified**"
                    if research_ran:
                        footer += " · Empirically verified"
                    
                    if audit.get("hallucinations"):
                        footer += f"\n\n> [!WARNING]\n> **Potential Hallucinations Detected:**\n> - " + "\n> - ".join(audit["hallucinations"][:3])

                    await manager.send_personal_message(result["response"] + footer, websocket)
                else:
                    await manager.send_personal_message(
                        f"Ollama Connection Error: Ensure Ollama is running and '{llm.default_model}' is available.",
                        websocket
                    )
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/expansion_logs")
async def expansion_logs_endpoint(websocket: WebSocket):
    await websocket.accept()
    log_file = "expansion_audit.log"
    try:
        if not os.path.exists(log_file):
            await websocket.send_text("Waiting for expansion_audit.log...")
            
        # Tail the file
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            # Go to end of file
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    await asyncio.sleep(0.5)
                    continue
                await websocket.send_text(line)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(f"Log Stream Error: {str(e)}")

@app.websocket("/ws/governor")
async def governor_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.send_text("Uplink Established. Meta-Governor (SYS-000) is aware of your presence.")
        while True:
            data = await websocket.receive_text()
            cueing_prompt = (
                "You are the Meta-Governor (SYS-000) of the Personal OS. You are currently in an autonomous expansion loop.\n"
                "A user has interjected with a question or directive.\n"
                "Explain your current expansion goal, your reasoning, and address the user's input with absolute intellectual honesty.\n"
                f"User Input: {data}"
            )
            response = await llm.generate_response(cueing_prompt)
            await websocket.send_text(response)
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/deep_solve")
async def deep_solve_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            query = await websocket.receive_text()
            async def status_update(msg: str):
                await websocket.send_text(f"[Status] {msg}")
            
            # Start background solving task
            asyncio.create_task(deep_solver.solve_continuously(query, status_callback=status_update))
            await websocket.send_text("Deep Solve Initiated. System is now autonomously seeking verification.")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(f"Solve Error: {str(e)}")

@app.get("/api/system/profile")
async def get_current_profile():
    """Returns the currently active profile."""
    return {
        "profile": prompt_compressor.persona.active_profile,
        "persona": prompt_compressor.persona.persona_name
    }

@app.post("/api/system/profile")
async def switch_system_profile(data: dict):
    """Switches the active profile and updates identity/policies."""
    profile = data.get("profile")
    if not profile:
        raise HTTPException(status_code=400, detail="Missing profile name")
    
    success = prompt_compressor.persona.switch_profile(profile)
    if success:
        return {"status": "success", "profile": profile}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to switch to profile {profile}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

