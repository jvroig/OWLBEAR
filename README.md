# OWLBEAR
![OWLBEAR logo](images/owlbear_logo.png)
OWLBEAR: Orchestrated Workflow Logic with Bespoke Experts for Agentic Routines

## Overview
OWLBEAR is a framework designed to simplify the creation and management of agentic AI workflows. By combining Orchestrated Workflow Logic with Bespoke Experts , OWLBEAR empowers developers and enterprises to build reliable, scalable, and customizable AI-driven solutions.

Whether you're automating business processes, solving complex problems, or fostering innovation, OWLBEAR provides the tools and structure needed to streamline your workflows and achieve your goals.


## Key Features
- Modular Expert System : Leverage a library of pre-defined experts (e.g., Executive Coach, Strategic Thinking Partner,Communication Strategist) or create your own bespoke experts tailored to your needs.
- Customizable Endpoints : Connect to various LLMs and APIs by configuring endpoints for each expert.
- Orchestrated Workflows : Seamlessly integrate multiple experts into cohesive workflows that align with your business objectives.
- Agentic Routines : Enable AI agents to execute tasks autonomously, reason through challenges, and adapt to dynamic environments by combining orchestrated workflows with tool-using experts.

## Installation
To get started with OWLBEAR, follow these steps:

1. Clone the repository:
```bash
git clone https://github.com/jvroig/OWLBEAR.git
cd OWLBEAR
```

2. Create virtual environment and install requirements:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Copy `endpoint_config_sample.yaml` to `endpoint_config.yaml`
```bash
cp endpoint_config_sample.yaml endpoint_config.yaml
```

4. Open `endpoint_config.yaml` in your editor and update with your actual endpoint information.

5. Create a `.env` file in the project's root directory to place your API KEY. See "Experts" section for matching API Key values in .env with endpoint config. 

## Usage
To run one of the sample workflows:
```bash
python3 owlbear.py workflows/databreach.yml
```
In this simple example, 3 experts work together to create a data breach response plan:
- CEO
- Strategic Thinking Partner
- Ethical Decision Making Counselor

After that runs, you can view the outputs in the `outputs/databreach_[timestamp]/` folder

## Experts
You can define your own AI Experts in the `experts` folder.

Use the pre-built sample experts as a template.

The `ApiKey` property defines which entry in your `.env` file should be used. For example:
```yaml
ExpertID: MyExpert
Description: Testing
SystemPrompt: Awesome prompt here
Endpoint:
  Host: "127.0.0.1"
  Port: "8000"
  Model: "Qwen/Qwen2.5-72B-Instruct"
ApiKey: MY_SECRET_API_KEY
```

The above will work if MY_SECRET_API_KEY exists in the `.env` file at the root of the project:
```
MY_SECRET_API_KEY=abcdef42069
```

`ApiKey` can be the API Key for any LLM API endpoint - OpenAI, Anthropic, Alibaba Cloud Model Studio, etc. You can store an unlimited number of API keys in `.env`.