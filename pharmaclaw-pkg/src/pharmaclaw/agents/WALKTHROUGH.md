# PharmaClaw AI Agents — Getting Started Guide 🧪

## What Are PharmaClaw Agents?

PharmaClaw agents are AI-powered wrappers around computational chemistry tools.
You ask questions in plain English, and the AI figures out which tools to run,
executes them, and explains the results.

**No OpenClaw needed. No complex setup. Just pip install and go.**

---

## Step 1: Install

```bash
pip install pharmaclaw[agents]
```

This installs:
- PharmaClaw computational tools (RDKit-based)
- AI agent wrappers
- litellm (supports OpenAI, Anthropic, Google, Ollama, and 100+ LLM providers)

> **Note:** If `pip install rdkit` fails, use conda instead:
> ```bash
> conda install -c conda-forge rdkit
> pip install pharmaclaw[agents]
> ```

---

## Step 2: Get an API Key

You need an API key from any supported LLM provider:

| Provider | Get Key | Cost | Model |
|----------|---------|------|-------|
| **OpenAI** | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | ~$0.15/1M tokens | `gpt-4o-mini` |
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com) | ~$3/1M tokens | `claude-sonnet-4-20250514` |
| **Google** | [aistudio.google.com](https://aistudio.google.com) | Free tier available | `gemini/gemini-pro` |
| **Ollama** | [ollama.com](https://ollama.com) | Free (runs locally) | `ollama/llama3` |
| **Mistral** | [console.mistral.ai](https://console.mistral.ai) | ~$0.25/1M tokens | `mistral/mistral-large-latest` |

**Cheapest option:** OpenAI `gpt-4o-mini` (~$0.15 per million tokens — a full drug analysis costs < $0.01)

**Free option:** Ollama (runs on your machine, no internet needed, no cost)

---

## Step 3: Configure

### Option A: Interactive setup (recommended)
```bash
pharmaclaw setup
```
Follow the prompts. It saves your key to `~/.pharmaclaw/config.json`.

### Option B: Environment variable
```bash
export OPENAI_API_KEY="sk-proj-..."
```

### Option C: Pass directly
```python
from pharmaclaw.agents import ChemistryAgent
agent = ChemistryAgent(api_key="sk-proj-...")
```

---

## Step 4: Start Using!

### CLI — Ask questions from terminal
```bash
# Ask the chemistry agent
pharmaclaw ask "What are the properties of aspirin?"

# Ask a specific agent
pharmaclaw ask "Profile ibuprofen for oral bioavailability" --agent pharmacology
pharmaclaw ask "Is benzene toxic?" --agent toxicology
pharmaclaw ask "Find papers on KRAS G12C inhibitors" --agent literature

# Run the full pipeline (all agents)
pharmaclaw pipeline "Analyze CC(=O)Oc1ccccc1C(=O)O as a drug candidate"

# Verbose mode — see which tools the AI calls
pharmaclaw pipeline "Full safety analysis of sotorasib" --verbose
```

### Python — Use in scripts or Jupyter
```python
from pharmaclaw.agents import ChemistryAgent, PharmacologyAgent, Pipeline

# Single agent
chem = ChemistryAgent(api_key="sk-...")
result = chem.ask("What is the molecular weight and LogP of sotorasib?")
print(result["answer"])

# ADME profiling
pharm = PharmacologyAgent(api_key="sk-...")
result = pharm.ask("Is CC(=O)Oc1ccccc1C(=O)O a good oral drug candidate?")
print(result["answer"])

# Full pipeline — all 9 agents
pipe = Pipeline(api_key="sk-...", model="gpt-4o", verbose=True)
report = pipe.run("Comprehensive analysis of sotorasib as a KRAS G12C inhibitor")
print(report["answer"])

# Access raw data from each tool
print(report["data"])        # dict of tool results
print(report["tool_calls"])  # list of what the AI called
```

### Jupyter Notebook
```python
# Cell 1: Install (run once)
!pip install pharmaclaw[agents]

# Cell 2: Setup
from pharmaclaw.agents import Pipeline
pipe = Pipeline(api_key="sk-...", verbose=True)

# Cell 3: Analyze
report = pipe.run("Analyze aspirin: properties, ADME, toxicity, and IP risk")
print(report["answer"])
```

---

## The 9 Agents

| Agent | CLI flag | What it does |
|-------|----------|-------------|
| 🧪 Chemistry | `--agent chemistry` | Molecular properties, fingerprints, retrosynthesis |
| 💊 Pharmacology | `--agent pharmacology` | ADME/PK, Lipinski, QED, BBB, CYP3A4 |
| ☠️ Toxicology | `--agent toxicology` | Safety screening, PAINS, risk scoring |
| 🔬 Synthesis | `--agent synthesis` | Route planning, feasibility scoring |
| 🔧 Catalyst | `--agent catalyst` | Catalyst recommendation, ligand design |
| 📚 Literature | `--agent literature` | PubMed + Semantic Scholar search |
| 💼 IP Check | `--agent ip` | Freedom-to-Operate, bioisostere suggestions |
| 📊 Market Intel | `--agent market` | FDA FAERS adverse events |
| 🎯 Pipeline | `pharmaclaw pipeline` | All agents orchestrated by AI |

---

## Using Ollama (Free, Local, Private)

For labs that can't send data to the cloud:

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a model
ollama pull llama3

# 3. Configure PharmaClaw
pharmaclaw setup
# When prompted: model = ollama/llama3, API key = (leave blank)

# 4. Use it
pharmaclaw ask "Analyze ethanol" --model ollama/llama3
```

---

## FAQ

**Q: Do I need OpenClaw?**
No. PharmaClaw is a standalone Python package. OpenClaw is not required.

**Q: How much does it cost?**
The PharmaClaw package is free and open source (MIT). You pay only for LLM API usage.
A full drug analysis with gpt-4o-mini costs about $0.005 (half a cent).

**Q: Can I use it without an API key?**
Yes! The computational tools work without any API key:
```bash
pharmaclaw chemistry -s "CCO" --mode props --pretty
pharmaclaw pharmacology -s "CCO" --pretty
```
The AI agents (ask, pipeline) require an API key.

**Q: Is my data sent to the cloud?**
Only if you use a cloud LLM (OpenAI, Anthropic, etc.). All RDKit computations
run locally. Use Ollama for fully local, private analysis.

**Q: Which model is best?**
- Best quality: `gpt-4o` or `claude-sonnet-4-20250514`
- Best value: `gpt-4o-mini` (great quality, very cheap)
- Free/private: `ollama/llama3`

---

## Need Help?

- 🌐 Website: https://pharmaclaw.com
- 📧 Email: cheminem602@gmail.com
- 💬 Discord: https://discord.com/invite/clawd
- 🐛 Issues: https://github.com/CheminemPharmaclaw/pharmaclaw/issues
