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

