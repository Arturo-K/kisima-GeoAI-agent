# Kisima GeoAgent for Seismic Data Analysis

This prototype demonstrate Kisima GeoAI functionality: An AI-powered geospatial analysis platform that translates natural language queries into seismic risk assessments and spatial analyses. Built with LangChain, LangGraph, Ollama and Gradio.

![Platform Demo](media/kisima-GeoAI-demo.mp4)

## Overview

This application demonstrates advanced GeoAI capabilities by combining:
- **Natural Language Processing**: Convert plain English queries into geospatial analyses
- **AI Agent Architecture**: LangGraph-based agent with multiple specialized tools
- **Interactive Visualization**: Real-time map updates and data exploration
- **Seismic Risk Analysis**: Comprehensive building vulnerability assessments

## Key Features
### Geospatial Analysis
- Building location searches with radius filtering
- Seismic risk zone identification
- Critical infrastructure mapping
- Building density calculations

### Data Visualization
- Interactive Folium map
- Layered geospatial data display
- Custom styling for risk zones

### AI-Powered Tools
- search_buildings_by_location: Find buildings near coordinates
- analyze_seismic_risk: Assess risk by zone
- calculate_building_density: Compute density metrics
- find_critical_infrastructure: Locate key facilities
- get_seismic_history: Retrieve earthquake data

## Architecture

```
geoAI-agent/
├── app.py                      # Gradio UI with chat interface
├── agent/
│   ├── config.py
│   ├── graph.py               # LangGraph agent orchestration
│   ├── tools.py               # Geospatial analysis tools
│   └── prompts.py             # System prompts and templates
├── data/
│   └── data_scraper.py            #data scraping tool (will be added to agent capability later)
│   └── nairobi_buildings.geojson  # Sample geospatial data
├── requirements.txt
├── .env.example
└── README.md
```

### Technology Stack

**AI & LLM**
- LangChain: Framework for LLM applications
- LangGraph: Agent workflow orchestration
- glm-4.6:cloud : Advanced reasoning and tool use

**Geospatial**
- GeoPandas: Geospatial data manipulation
- Folium: Interactive mapping
- Shapely: Geometric operations

**UI/UX**
- Streamlit: Web application framework
- Custom CSS: Modern, responsive design

## Set up
### Prerequisites
- Python 3.9 or higher
- Ollama with glm-4.6:cloud

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd geoai-mvp
```

2. **Create & activate virtual environment**
```bash
python -m venv venv

#for mac
source venv/bin/activate  

# On Windows
venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env and add your OLLAMA_API_KEY
```

5. **Add geospatial data**
Place your `example.geojson` file in the `data/` directory.

### Running the Application

```bash
python app.py
```

The application will open in your browser at `http://localhost:8001`


## Contributing

This is a portfolio/demo project. Feel free to fork and adapt for your needs!

## License

Apache License - feel free to use this for your portfolio or projects.

## Learning Resources

- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Guide](https://langchain-ai.github.io/langgraph/)
- [GeoPandas Tutorial](https://geopandas.org/)

## About

I Built this as a portfolio project demonstrating:
- AI agent development with LangGraph
- Natural language to geospatial query translation
- Professional software architecture

---

**Note**: This is a demonstration project. For production use, implement proper authentication, rate limiting, and data validation.

