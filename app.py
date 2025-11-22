import gradio as gr
import folium
import logging
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

from agent.graph import build_graph
from agent.config import AgentConfig
from agent.tools import load_geospatial_data

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MapRenderer:
    """Handles all map generation and visualization logic."""
    
    DEFAULT_CENTER = (-1.2864, 36.8172)
    DEFAULT_ZOOM = 13
    
    def __init__(self):
        # DON'T load full dataset - use simplified version
        from agent.tools import load_simplified_display_data
        self.gdf = load_simplified_display_data()
        logger.info(f"MapRenderer initialized with {len(self.gdf) if self.gdf is not None else 0} display features")
        
    def generate(
        self, 
        center: Optional[Tuple[float, float]] = None,
        zoom: int = DEFAULT_ZOOM,
        highlight_coords: Optional[Tuple[float, float]] = None,
        markers: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Generate HTML for Folium map with optional highlights."""
        center = center or self.DEFAULT_CENTER
        
        m = folium.Map(
            location=center, 
            zoom_start=zoom,
            tiles='CartoDB positron'
        )
        
        # Add background risk layer
        if self.gdf is not None:
            self._add_risk_layer(m)
        
        # Add highlight marker
        if highlight_coords:
            self._add_highlight(m, highlight_coords)
        
        # Add custom markers
        if markers:
            self._add_markers(m, markers)
            
        return m._repr_html_()
    
    def _add_risk_layer(self, map_obj: folium.Map) -> None:
        """Add geospatial risk layer to map."""
        folium.GeoJson(
            self.gdf,
            name="Risk Layer",
            style_function=lambda x: {
                'fillColor': '#ef4444' if x['properties'].get('risk_level') == 'high' else '#3b82f6',
                'color': 'none',
                'fillOpacity': 0.6
            },
            tooltip=folium.GeoJsonTooltip(fields=['name', 'risk_level'])
        ).add_to(map_obj)
    
    def _add_highlight(self, map_obj: folium.Map, coords: Tuple[float, float]) -> None:
        """Add highlighted location marker."""
        folium.Marker(
            location=coords,
            popup="Target Location",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(map_obj)
        
        folium.Circle(
            location=coords,
            radius=500,
            color="#ef4444",
            fill=True,
            fillOpacity=0.3
        ).add_to(map_obj)
    
    def _add_markers(self, map_obj: folium.Map, markers: List[Dict[str, Any]]) -> None:
        """Add custom markers from agent results."""
        for marker in markers:
            folium.Marker(
                location=marker.get('coords'),
                popup=marker.get('popup', ''),
                icon=folium.Icon(
                    color=marker.get('color', 'blue'),
                    icon=marker.get('icon', 'info-sign')
                )
            ).add_to(map_obj)


class GeoChatUI:
    """Simplified UI - state management moved to graph."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.graph = build_graph(config)
        self.map_renderer = MapRenderer()
        self.thread_id = "kisima_session"
        self.demo = None
    
    def build_interface(self):
        """Build Gradio interface."""
        demo = gr.Blocks(title="Kisima GeoAI")
        
        with demo:
            gr.Markdown("## 🌍 Kisima GeoAI\n**Seismic Analysis & Risk Intelligence**")
            
            with gr.Row():
                with gr.Column(scale=4, min_width=400):
                    chatbot = gr.Chatbot(height=600, show_label=False)
                    
                    with gr.Row():
                        msg_input = gr.Textbox(
                            placeholder="Ask about seismic risks, buildings, or density...",
                            show_label=False,
                            container=False,
                            scale=8
                        )
                        submit_btn = gr.Button("Send", variant="primary", scale=1)
                    
                    clear_btn = gr.Button("Clear History", size="sm")
                    
                    gr.Examples(
                        examples=[
                            "Find hospitals within 1km of -1.2864, 36.8172",
                            "Analyze seismic risk for high-rise buildings",
                            "Calculate building density in Westlands",
                        ],
                        inputs=msg_input
                    )
                
                with gr.Column(scale=6, min_width=500):
                    gr.Markdown("### 🗺️ Live Geospatial Context")
                    map_display = gr.HTML(value=self.map_renderer.generate(), label="Geospatial View")
                    
                    with gr.Accordion("Analysis Details", open=True):
                        metrics_panel = gr.JSON(value={"status": "ready"}, label="Agent Diagnostics")
            
            # Event handlers
            msg_input.submit(
                self._handle_message,
                inputs=[msg_input, chatbot],
                outputs=[chatbot, map_display, metrics_panel, msg_input]
            )
            
            submit_btn.click(
                self._handle_message,
                inputs=[msg_input, chatbot],
                outputs=[chatbot, map_display, metrics_panel, msg_input]
            )
            
            clear_btn.click(
                self._clear_history,
                outputs=[chatbot, map_display, metrics_panel]
            )
        
        self.demo = demo
        return demo
    
    def _handle_message(self, user_message: str, history: List[Dict]) -> tuple:
        """Handle message through graph."""
        if not user_message.strip():
            return history, gr.update(), gr.update(), ""
        
        try:
            # Run graph with conversation memory
            input_state = {"messages": [HumanMessage(content=user_message)]}
            config = {"configurable": {"thread_id": self.thread_id}}
            result = self.graph.invoke(input_state, config)
            
            # Update UI
            history = history or []
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": result["response"]})
            
            map_html = self.map_renderer.generate(
                center=result.get("location"),
                highlight_coords=result.get("location"),
                markers=result.get("markers")
            )
            
            metrics = {
                'status': 'success',
                'tools_used': result["metadata"].get('tools_used', []),
                'location_found': result.get("location") is not None,
                'markers_count': len(result["markers"]) if result.get("markers") else 0,
            }
            
            return history, map_html, metrics, ""
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            history = history or []
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": f"Error: {str(e)}"})
            return history, gr.update(), {"status": "error", "error": str(e)}, ""
    
    def _clear_history(self):
        """Reset conversation."""
        self.graph = build_graph(self.config)  # Fresh graph with empty memory
        return [], self.map_renderer.generate(), {"status": "reset"}
    
    def launch(self, **kwargs):
        if self.demo is None:
            self.build_interface()
        self.demo.launch(**kwargs)

def main():
    config = AgentConfig()
    app = GeoChatUI(config)
    app.launch(
        share=True, 
        server_name="0.0.0.0", 
        server_port=8001, 
        show_error=True)

if __name__ == "__main__":
    main()