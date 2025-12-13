"""
Aurora Browser - AI-Enhanced Web Browser
Opera-inspired browser with AI baked into the core
Includes AI content summarization, voice browsing, and intelligent features
"""

import os
import sys
import json
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
import logging
from datetime import datetime
import tempfile
import hashlib

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('WebKit2', '4.1')
    from gi.repository import Gtk, Adw, Gdk, Gio, GLib, Pango, WebKit2
    GTK_AVAILABLE = True
except ImportError:
    GTK_AVAILABLE = False

try:
    import requests
    from bs4 import BeautifulSoup
    import nltk
    from transformers import pipeline
    AI_FEATURES_AVAILABLE = True
except ImportError:
    AI_FEATURES_AVAILABLE = False

from ...ai_assistant.core.local_llm_engine import get_llm_engine
from ...ai_assistant.voice.voice_interface import get_voice_interface

@dataclass
class BrowserTab:
    """Browser tab information"""
    id: str
    title: str
    url: str
    webview: Any = None
    loading: bool = False
    can_go_back: bool = False
    can_go_forward: bool = False
    favicon_url: Optional[str] = None
    last_visited: datetime = field(default_factory=datetime.now)

@dataclass
class AIInsight:
    """AI-generated insight about web content"""
    type: str  # summary, key_points, sentiment, translation
    content: str
    confidence: float
    generated_at: datetime = field(default_factory=datetime.now)

class AuroraBrowser:
    """
    AI-enhanced web browser for Aurora OS
    Features AI summarization, voice browsing, and intelligent content analysis
    """
    
    def __init__(self):
        self.tabs: Dict[str, BrowserTab] = {}
        self.active_tab_id: Optional[str] = None
        self.llm_engine = get_llm_engine()
        self.voice_interface = get_voice_interface()
        
        # AI Features
        self.ai_summarizer = None
        self.ai_insights: Dict[str, List[AIInsight]] = {}
        
        # UI Components
        self.window = None
        self.tab_bar = None
        self.webview_container = None
        self.url_bar = None
        self.ai_panel = None
        
        # Settings
        self.settings = self._load_settings()
        
        self.logger = logging.getLogger("Aurora.Browser")
        self._setup_logging()
        
        # Initialize AI features
        self._init_ai_features()
        
        # Initialize UI
        if GTK_AVAILABLE:
            self._init_ui()
    
    def _setup_logging(self):
        """Setup logging"""
        log_dir = Path("/var/log/aurora")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_dir / "aurora_browser.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load browser settings"""
        settings_file = Path.home() / ".config" / "aurora" / "browser_settings.json"
        
        default_settings = {
            'ai_summarization_enabled': True,
            'voice_browsing_enabled': True,
            'ad_blocking_enabled': True,
            'tracker_blocking_enabled': True,
            'privacy_mode': False,
            'dark_mode': False,
            'default_search_engine': 'duckduckgo',
            'home_page': 'aurora://home',
            'ai_insight_types': ['summary', 'key_points', 'sentiment'],
            'auto_summarize_long_articles': True,
            'voice_navigation_enabled': True,
            'reading_mode_enabled': True
        }
        
        try:
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    default_settings.update(loaded_settings)
        except:
            pass
        
        return default_settings
    
    def _init_ai_features(self):
        """Initialize AI features"""
        if not AI_FEATURES_AVAILABLE:
            self.logger.warning("AI features not available")
            return
        
        try:
            # Initialize summarization pipeline
            self.ai_summarizer = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                tokenizer="facebook/bart-large-cnn"
            )
            
            # Download required NLTK data
            try:
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
            except:
                pass
            
            self.logger.info("AI features initialized")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize AI features: {e}")
    
    def _init_ui(self):
        """Initialize the browser UI"""
        # Create main window
        self.window = Adw.Window()
        self.window.set_title("Aurora Browser")
        self.window.set_default_size(1400, 900)
        self.window.set_resizable(True)
        
        # Apply browser theme
        self._apply_browser_theme()
        
        # Create main layout
        self._create_main_layout()
        
        # Create first tab
        self._create_new_tab()
        
        # Connect signals
        self._connect_signals()
        
        self.logger.info("Aurora Browser UI initialized")
    
    def _apply_browser_theme(self):
        """Apply Aurora browser theme"""
        if self.window is None:
            return
        
        css_provider = Gtk.CssProvider()
        css_data = """
        window {
            background: #f8f9fa;
        }
        
        .tab-bar {
            background: linear-gradient(135deg, rgba(88, 86, 214, 0.1), rgba(175, 82, 222, 0.1));
            border-bottom: 1px solid rgba(0, 0, 0, 0.1);
        }
        
        .tab-button {
            background: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(0, 0, 0, 0.1);
            border-radius: 8px 8px 0 0;
            padding: 8px 16px;
            margin: 4px 2px 0 0;
            transition: all 0.3s ease;
        }
        
        .tab-button:hover {
            background: rgba(255, 255, 255, 0.9);
            transform: translateY(-1px);
        }
        
        .tab-button.active {
            background: white;
            border-bottom-color: white;
            box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
        }
        
        .url-bar {
            background: white;
            border: 2px solid #5856d6;
            border-radius: 24px;
            padding: 12px 20px;
            margin: 8px;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        .url-bar:focus {
            border-color: #af52de;
            box-shadow: 0 0 0 3px rgba(88, 86, 214, 0.1);
        }
        
        .navigation-button {
            background: linear-gradient(135deg, #5856d6, #af52de);
            color: white;
            border: none;
            border-radius: 50%;
            min-width: 36px;
            min-height: 36px;
            margin: 8px 4px;
            transition: all 0.3s ease;
        }
        
        .navigation-button:hover {
            transform: scale(1.1);
            box-shadow: 0 4px 12px rgba(88, 86, 214, 0.3);
        }
        
        .navigation-button:disabled {
            background: #e0e0e0;
            transform: scale(1.0);
        }
        
        .ai-panel {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(240, 240, 255, 0.95));
            border-left: 2px solid #5856d6;
            border-radius: 12px 0 0 12px;
            padding: 20px;
            min-width: 300px;
            max-width: 400px;
        }
        
        .ai-insight-card {
            background: white;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            border-left: 4px solid #5856d6;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        .ai-insight-title {
            font-weight: bold;
            font-size: 14px;
            color: #5856d6;
            margin-bottom: 8px;
        }
        
        .ai-insight-content {
            font-size: 13px;
            color: #333;
            line-height: 1.5;
        }
        
        .ai-status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #30d158;
            display: inline-block;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .loading-spinner {
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        """
        
        css_provider.load_from_data(css_data.encode())
        
        # Apply to display
        style_context = self.window.get_style_context()
        style_context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    
    def _create_main_layout(self):
        """Create the main browser layout"""
        # Create vertical box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.set_child(main_box)
        
        # Create header with tab bar and navigation
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(header_box)
        
        # Tab bar
        self.tab_bar = self._create_tab_bar()
        header_box.append(self.tab_bar)
        
        # Navigation bar
        nav_bar = self._create_navigation_bar()
        header_box.append(nav_bar)
        
        # Create content area with webview and AI panel
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.append(content_box)
        
        # Webview container
        self.webview_container = Gtk.Stack()
        self.webview_container.set_hexpand(True)
        self.webview_container.set_vexpand(True)
        content_box.append(self.webview_container)
        
        # AI panel
        self.ai_panel = self._create_ai_panel()
        if self.settings['ai_summarization_enabled']:
            content_box.append(self.ai_panel)
    
    def _create_tab_bar(self) -> Gtk.Widget:
        """Create the tab bar"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.add_css_class("tab-bar")
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        
        # New tab button
        new_tab_button = Gtk.Button(label="+")
        new_tab_button.add_css_class("tab-button")
        new_tab_button.set_tooltip_text("New Tab")
        new_tab_button.connect("clicked", self._on_new_tab_clicked)
        box.append(new_tab_button)
        
        # Tabs box
        self.tabs_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.tabs_box.set_hexpand(True)
        box.append(self.tabs_box)
        
        return box
    
    def _create_navigation_bar(self) -> Gtk.Widget:
        """Create the navigation bar"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_bottom(8)
        
        # Back button
        self.back_button = Gtk.Button()
        self.back_button.set_icon_name("go-previous-symbolic")
        self.back_button.add_css_class("navigation-button")
        self.back_button.set_tooltip_text("Back")
        self.back_button.set_sensitive(False)
        self.back_button.connect("clicked", self._on_back_clicked)
        box.append(self.back_button)
        
        # Forward button
        self.forward_button = Gtk.Button()
        self.forward_button.set_icon_name("go-next-symbolic")
        self.forward_button.add_css_class("navigation-button")
        self.forward_button.set_tooltip_text("Forward")
        self.forward_button.set_sensitive(False)
        self.forward_button.connect("clicked", self._on_forward_clicked)
        box.append(self.forward_button)
        
        # Refresh button
        self.refresh_button = Gtk.Button()
        self.refresh_button.set_icon_name("view-refresh-symbolic")
        self.refresh_button.add_css_class("navigation-button")
        self.refresh_button.set_tooltip_text("Refresh")
        self.refresh_button.connect("clicked", self._on_refresh_clicked)
        box.append(self.refresh_button)
        
        # Home button
        self.home_button = Gtk.Button()
        self.home_button.set_icon_name("go-home-symbolic")
        self.home_button.add_css_class("navigation-button")
        self.home_button.set_tooltip_text("Home")
        self.home_button.connect("clicked", self._on_home_clicked)
        box.append(self.home_button)
        
        # URL bar
        self.url_bar = Gtk.Entry()
        self.url_bar.add_css_class("url-bar")
        self.url_bar.set_hexpand(True)
        self.url_bar.set_placeholder_text("Search or enter address...")
        self.url_bar.connect("activate", self._on_url_bar_activated)
        box.append(self.url_bar)
        
        # Voice search button
        if self.settings['voice_browsing_enabled']:
            self.voice_button = Gtk.Button()
            self.voice_button.set_icon_name("audio-input-microphone-symbolic")
            self.voice_button.add_css_class("navigation-button")
            self.voice_button.set_tooltip_text("Voice Search")
            self.voice_button.connect("clicked", self._on_voice_search_clicked)
            box.append(self.voice_button)
        
        # AI Insights button
        self.ai_button = Gtk.Button()
        self.ai_button.set_icon_name("brain-symbolic")
        self.ai_button.add_css_class("navigation-button")
        self.ai_button.set_tooltip_text("AI Insights")
        self.ai_button.connect("clicked", self._on_ai_insights_clicked)
        box.append(self.ai_button)
        
        # Settings button
        self.settings_button = Gtk.Button()
        self.settings_button.set_icon_name("preferences-system-symbolic")
        self.settings_button.add_css_class("navigation-button")
        self.settings_button.set_tooltip_text("Browser Settings")
        self.settings_button.connect("clicked", self._on_settings_clicked)
        box.append(self.settings_button)
        
        return box
    
    def _create_ai_panel(self) -> Gtk.Widget:
        """Create the AI insights panel"""
        # Create scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_width(350)
        scrolled.set_max_content_width(400)
        
        # AI panel content
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.add_css_class("ai-panel")
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        
        # AI status header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        ai_status = Gtk.Label()
        ai_status.add_css_class("ai-status-indicator")
        header_box.append(ai_status)
        
        ai_title = Gtk.Label(label="AI Insights")
        ai_title.add_css_class("title-4")
        header_box.append(ai_title)
        
        box.append(header_box)
        
        # Insights container
        self.insights_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.append(self.insights_container)
        
        # Loading indicator
        self.ai_loading_label = Gtk.Label(label="Analyzing content...")
        self.ai_loading_label.add_css_class("body")
        self.ai_loading_label.add_css_class("dim-label")
        box.append(self.ai_loading_label)
        
        scrolled.set_child(box)
        return scrolled
    
    def _create_new_tab(self, url: str = None):
        """Create a new browser tab"""
        tab_id = f"tab_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.tabs)}"
        
        # Create webview
        webview = WebKit2.WebView()
        webview.set_hexpand(True)
        webview.set_vexpand(True)
        
        # Create tab object
        tab = BrowserTab(
            id=tab_id,
            title="New Tab",
            url=url or self.settings['home_page'],
            webview=webview
        )
        
        # Configure webview
        self._configure_webview(webview, tab)
        
        # Add to tabs
        self.tabs[tab_id] = tab
        self.webview_container.add_named(webview, tab_id)
        
        # Create tab button
        tab_button = self._create_tab_button(tab)
        self.tabs_box.append(tab_button)
        
        # Set as active tab
        self.switch_to_tab(tab_id)
        
        # Load URL
        if url:
            webview.load_uri(url)
        else:
            self._load_new_tab_page(webview)
        
        self.logger.info(f"Created new tab: {tab_id}")
    
    def _configure_webview(self, webview: WebKit2.WebView, tab: BrowserTab):
        """Configure webview with settings and event handlers"""
        # Set user agent
        webview.set_user_agent("Aurora Browser/1.0 (AI-Enhanced)")
        
        # Enable developer tools
        context = webview.get_context()
        context.set_web_extensions_directory("/usr/lib/aurora-browser/extensions")
        
        # Connect signals
        webview.connect("load-changed", self._on_load_changed, tab)
        webview.connect("load-failed", self._on_load_failed, tab)
        webview.connect("notify::title", self._on_title_changed, tab)
        webview.connect("notify::uri", self._on_uri_changed, tab)
        
        # Configure privacy settings
        settings = webview.get_settings()
        
        if self.settings['privacy_mode']:
            settings.set_enable_javascript(False)
            settings.set_enable_plugins(False)
        
        if self.settings['ad_blocking_enabled']:
            self._setup_ad_blocking(webview)
        
        if self.settings['tracker_blocking_enabled']:
            self._setup_tracker_blocking(webview)
    
    def _setup_ad_blocking(self, webview: WebKit2.WebView):
        """Setup ad blocking for webview"""
        # This would integrate with ad-block lists
        # For now, we'll use a simple content filter
        pass
    
    def _setup_tracker_blocking(self, webview: WebKit2.WebView):
        """Setup tracker blocking for webview"""
        # This would integrate with privacy lists
        # For now, we'll use a simple content filter
        pass
    
    def _create_tab_button(self, tab: BrowserTab) -> Gtk.Widget:
        """Create a tab button"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.add_css_class("tab-button")
        
        # Favicon (placeholder)
        favicon = Gtk.Image.new_from_icon_name("text-html-symbolic")
        favicon.set_pixel_size(16)
        box.append(favicon)
        
        # Title
        title_label = Gtk.Label(label=tab.title)
        title_label.set_max_width_chars(30)
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        box.append(title_label)
        
        # Close button
        close_button = Gtk.Button()
        close_button.set_icon_name("window-close-symbolic")
        close_button.add_css_class("flat")
        close_button.connect("clicked", self._on_close_tab_clicked, tab.id)
        box.append(close_button)
        
        # Store tab ID and connect click
        box.tab_id = tab.id
        gesture_click = Gtk.GestureClick()
        gesture_click.connect("pressed", self._on_tab_clicked)
        box.add_controller(gesture_click)
        
        return box
    
    def _load_new_tab_page(self, webview: WebKit2.WebView):
        """Load the new tab page"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>New Tab - Aurora Browser</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    margin: 0;
                    padding: 0;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    color: white;
                }
                .container {
                    text-align: center;
                    max-width: 600px;
                    padding: 40px;
                }
                .logo {
                    font-size: 48px;
                    margin-bottom: 20px;
                }
                h1 {
                    font-size: 32px;
                    margin-bottom: 10px;
                    font-weight: 300;
                }
                .search-container {
                    margin: 40px 0;
                }
                .search-box {
                    background: rgba(255, 255, 255, 0.1);
                    border: 2px solid rgba(255, 255, 255, 0.3);
                    border-radius: 50px;
                    padding: 16px 24px;
                    font-size: 16px;
                    width: 100%;
                    max-width: 400px;
                    color: white;
                    backdrop-filter: blur(10px);
                    transition: all 0.3s ease;
                }
                .search-box:focus {
                    outline: none;
                    border-color: white;
                    background: rgba(255, 255, 255, 0.2);
                }
                .search-box::placeholder {
                    color: rgba(255, 255, 255, 0.7);
                }
                .quick-links {
                    margin-top: 40px;
                }
                .quick-link {
                    display: inline-block;
                    margin: 10px;
                    padding: 12px 20px;
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 25px;
                    color: white;
                    text-decoration: none;
                    transition: all 0.3s ease;
                    backdrop-filter: blur(10px);
                }
                .quick-link:hover {
                    background: rgba(255, 255, 255, 0.2);
                    transform: translateY(-2px);
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">🌌</div>
                <h1>Welcome to Aurora Browser</h1>
                <p>AI-powered browsing with intelligent insights</p>
                
                <div class="search-container">
                    <input type="text" class="search-box" placeholder="Search the web or enter a URL..." id="searchInput" autofocus>
                </div>
                
                <div class="quick-links">
                    <a href="https://duckduckgo.com" class="quick-link">Search</a>
                    <a href="https://news.ycombinator.com" class="quick-link">News</a>
                    <a href="https://github.com" class="quick-link">GitHub</a>
                    <a href="https://stackoverflow.com" class="quick-link">Stack Overflow</a>
                </div>
            </div>
            
            <script>
                document.getElementById('searchInput').addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        let query = this.value.trim();
                        if (query) {
                            // Check if it's a URL or search query
                            if (query.includes('.') && !query.includes(' ')) {
                                window.location.href = query.startsWith('http') ? query : 'https://' + query;
                            } else {
                                window.location.href = 'https://duckduckgo.com/?q=' + encodeURIComponent(query);
                            }
                        }
                    }
                });
            </script>
        </body>
        </html>
        """
        
        # Load HTML content
        webview.load_html(html_content, "aurora://new-tab")
    
    def _on_tab_clicked(self, gesture, n_press, x, y):
        """Handle tab click"""
        widget = gesture.get_widget()
        tab_id = getattr(widget, 'tab_id', None)
        
        if tab_id:
            self.switch_to_tab(tab_id)
    
    def switch_to_tab(self, tab_id: str):
        """Switch to a specific tab"""
        if tab_id not in self.tabs:
            return
        
        self.active_tab_id = tab_id
        tab = self.tabs[tab_id]
        
        # Switch webview
        self.webview_container.set_visible_child_name(tab_id)
        
        # Update URL bar
        self.url_bar.set_text(tab.url)
        
        # Update navigation buttons
        self.back_button.set_sensitive(tab.can_go_back)
        self.forward_button.set_sensitive(tab.can_go_forward)
        
        # Update tab button styles
        for child in self.tabs_box.get_children():
            child.remove_css_class("active")
        
        # Find and highlight active tab button
        for child in self.tabs_box.get_children():
            if getattr(child, 'tab_id', None) == tab_id:
                child.add_css_class("active")
                break
        
        # Update AI insights
        self._update_ai_insights(tab_id)
        
        self.logger.info(f"Switched to tab: {tab_id}")
    
    def _on_load_changed(self, webview: WebKit2.WebView, load_event: WebKit2.LoadEvent, tab: BrowserTab):
        """Handle webview load events"""
        if load_event == WebKit2.LoadEvent.STARTED:
            tab.loading = True
            self._update_tab_button(tab)
        
        elif load_event == WebKit2.LoadEvent.COMMITTED:
            tab.can_go_back = webview.can_go_back()
            tab.can_go_forward = webview.can_go_forward()
            self._update_navigation_buttons()
        
        elif load_event == WebKit2.LoadEvent.FINISHED:
            tab.loading = False
            tab.title = webview.get_title() or "Untitled"
            tab.url = webview.get_uri() or "about:blank"
            
            self._update_tab_button(tab)
            self._update_navigation_buttons()
            self.url_bar.set_text(tab.url)
            
            # Generate AI insights
            if self.settings['ai_summarization_enabled']:
                asyncio.create_task(self._generate_ai_insights(tab))
    
    def _on_load_failed(self, webview: WebKit2.WebView, load_event: WebKit2.LoadEvent, failing_uri: str, error: GLib.Error, tab: BrowserTab):
        """Handle webview load failures"""
        self.logger.error(f"Failed to load {failing_uri}: {error.message}")
        tab.loading = False
        self._update_tab_button(tab)
    
    def _on_title_changed(self, webview: WebKit2.WebView, param_spec, tab: BrowserTab):
        """Handle title changes"""
        tab.title = webview.get_title() or "Untitled"
        self._update_tab_button(tab)
    
    def _on_uri_changed(self, webview: WebKit2.WebView, param_spec, tab: BrowserTab):
        """Handle URI changes"""
        tab.url = webview.get_uri() or "about:blank"
        
        if self.active_tab_id == tab.id:
            self.url_bar.set_text(tab.url)
    
    def _update_tab_button(self, tab: BrowserTab):
        """Update tab button appearance"""
        for child in self.tabs_box.get_children():
            if getattr(child, 'tab_id', None) == tab.id:
                # Update title
                title_label = child.get_first_child().get_next_sibling()
                if title_label:
                    title_label.set_label(tab.title)
                
                # Update loading state
                if tab.loading:
                    child.add_css_class("loading")
                else:
                    child.remove_css_class("loading")
                
                break
    
    def _update_navigation_buttons(self):
        """Update navigation button states"""
        if self.active_tab_id and self.active_tab_id in self.tabs:
            tab = self.tabs[self.active_tab_id]
            self.back_button.set_sensitive(tab.can_go_back)
            self.forward_button.set_sensitive(tab.can_go_forward)
    
    async def _generate_ai_insights(self, tab: BrowserTab):
        """Generate AI insights for the current page"""
        if not self.ai_summarizer:
            return
        
        try:
            # Get page content
            content = await self._extract_page_content(tab.webview)
            
            if not content or len(content) < 100:
                return
            
            # Generate insights
            insights = []
            
            # Summary
            if 'summary' in self.settings['ai_insight_types']:
                summary = await self._generate_summary(content)
                if summary:
                    insights.append(AIInsight(
                        type="summary",
                        content=summary,
                        confidence=0.8
                    ))
            
            # Key points
            if 'key_points' in self.settings['ai_insight_types']:
                key_points = await self._extract_key_points(content)
                if key_points:
                    insights.append(AIInsight(
                        type="key_points",
                        content=key_points,
                        confidence=0.7
                    ))
            
            # Store insights
            self.ai_insights[tab.id] = insights
            
            # Update UI if this is the active tab
            if self.active_tab_id == tab.id:
                self._update_ai_insights_display(tab.id)
        
        except Exception as e:
            self.logger.error(f"Failed to generate AI insights: {e}")
    
    async def _extract_page_content(self, webview: WebKit2.WebView) -> Optional[str]:
        """Extract text content from the current page"""
        try:
            # Use JavaScript to extract content
            script = """
                (function() {
                    // Remove unwanted elements
                    const unwanted = ['script', 'style', 'nav', 'header', 'footer', 'aside'];
                    unwanted.forEach(tag => {
                        document.querySelectorAll(tag).forEach(el => el.remove());
                    });
                    
                    // Extract main content
                    const content = document.body.innerText || '';
                    return content.trim();
                })();
            """
            
            result = await self._evaluate_javascript(webview, script)
            return result
        
        except Exception as e:
            self.logger.error(f"Failed to extract page content: {e}")
            return None
    
    async def _evaluate_javascript(self, webview: WebKit2.WebView, script: str) -> Optional[str]:
        """Evaluate JavaScript in webview"""
        try:
            # This would use WebKit's JavaScript evaluation
            # For now, return None as placeholder
            return None
        except:
            return None
    
    async def _generate_summary(self, content: str) -> Optional[str]:
        """Generate summary of content"""
        try:
            # Limit content length for summarization
            max_length = 1024
            if len(content) > max_length:
                content = content[:max_length] + "..."
            
            # Generate summary
            result = self.ai_summarizer(content, max_length=150, min_length=50, do_sample=False)
            return result[0]['summary_text']
        
        except Exception as e:
            self.logger.error(f"Failed to generate summary: {e}")
            return None
    
    async def _extract_key_points(self, content: str) -> Optional[str]:
        """Extract key points from content"""
        try:
            # Simple key point extraction using sentence tokenization
            sentences = content.split('.')
            
            # Score sentences by length and keywords
            scored_sentences = []
            for i, sentence in enumerate(sentences):
                if len(sentence.strip()) > 20:  # Ignore very short sentences
                    score = len(sentence.split())  # Simple scoring based on word count
                    scored_sentences.append((score, sentence.strip()))
            
            # Get top sentences
            scored_sentences.sort(reverse=True, key=lambda x: x[0])
            top_sentences = [s for score, s in scored_sentences[:5]]
            
            return '\n• '.join(top_sentences)
        
        except Exception as e:
            self.logger.error(f"Failed to extract key points: {e}")
            return None
    
    def _update_ai_insights(self, tab_id: str):
        """Update AI insights display"""
        insights = self.ai_insights.get(tab_id, [])
        
        # Clear existing insights
        for child in self.insights_container.get_children():
            self.insights_container.remove(child)
        
        if not insights:
            # Show loading or no insights message
            if self.tabs[tab_id].loading:
                self.ai_loading_label.set_text("Analyzing content...")
                self.ai_loading_label.set_visible(True)
            else:
                self.ai_loading_label.set_text("No insights available for this page")
                self.ai_loading_label.set_visible(True)
        else:
            self.ai_loading_label.set_visible(False)
            
            # Add insight cards
            for insight in insights:
                insight_card = self._create_insight_card(insight)
                self.insights_container.append(insight_card)
    
    def _create_insight_card(self, insight: AIInsight) -> Gtk.Widget:
        """Create a card for displaying an insight"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.add_css_class("ai-insight-card")
        
        # Title
        title = Gtk.Label(label=insight.type.replace('_', ' ').title())
        title.add_css_class("ai-insight-title")
        box.append(title)
        
        # Content
        content = Gtk.Label(label=insight.content)
        content.add_css_class("ai-insight-content")
        content.set_wrap(True)
        content.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        box.append(content)
        
        return box
    
    def _update_ai_insights_display(self, tab_id: str):
        """Update the AI insights display for a tab"""
        if self.active_tab_id == tab_id:
            self._update_ai_insights(tab_id)
    
    # Event handlers
    def _on_new_tab_clicked(self, button):
        """Handle new tab button click"""
        self._create_new_tab()
    
    def _on_close_tab_clicked(self, button, tab_id: str):
        """Handle tab close button click"""
        self.close_tab(tab_id)
    
    def _on_back_clicked(self, button):
        """Handle back button click"""
        if self.active_tab_id and self.active_tab_id in self.tabs:
            tab = self.tabs[self.active_tab_id]
            if tab.webview:
                tab.webview.go_back()
    
    def _on_forward_clicked(self, button):
        """Handle forward button click"""
        if self.active_tab_id and self.active_tab_id in self.tabs:
            tab = self.tabs[self.active_tab_id]
            if tab.webview:
                tab.webview.go_forward()
    
    def _on_refresh_clicked(self, button):
        """Handle refresh button click"""
        if self.active_tab_id and self.active_tab_id in self.tabs:
            tab = self.tabs[self.active_tab_id]
            if tab.webview:
                tab.webview.reload()
    
    def _on_home_clicked(self, button):
        """Handle home button click"""
        if self.active_tab_id and self.active_tab_id in self.tabs:
            tab = self.tabs[self.active_tab_id]
            if tab.webview:
                tab.webview.load_uri(self.settings['home_page'])
    
    def _on_url_bar_activated(self, entry):
        """Handle URL bar activation"""
        url = entry.get_text().strip()
        
        if not url:
            return
        
        # Check if it's a URL or search query
        if url.startswith('http://') or url.startswith('https://'):
            pass  # Already a URL
        elif '.' in url and ' ' not in url:
            url = 'https://' + url
        else:
            # Treat as search query
            search_engine = self.settings['default_search_engine']
            if search_engine == 'duckduckgo':
                url = f'https://duckduckgo.com/?q={url}'
            else:
                url = f'https://www.google.com/search?q={url}'
        
        # Load URL in active tab
        if self.active_tab_id and self.active_tab_id in self.tabs:
            tab = self.tabs[self.active_tab_id]
            if tab.webview:
                tab.webview.load_uri(url)
    
    def _on_voice_search_clicked(self, button):
        """Handle voice search button click"""
        # This would integrate with the voice interface
        pass
    
    def _on_ai_insights_clicked(self, button):
        """Handle AI insights button click"""
        # Toggle AI panel visibility
        if self.ai_panel.get_visible():
            self.ai_panel.set_visible(False)
        else:
            self.ai_panel.set_visible(True)
            if self.active_tab_id:
                self._update_ai_insights(self.active_tab_id)
    
    def _on_settings_clicked(self, button):
        """Handle settings button click"""
        # Open browser settings
        pass
    
    def _connect_signals(self):
        """Connect window signals"""
        if self.window:
            self.window.connect("close-request", self._on_window_close)
    
    def _on_window_close(self, window):
        """Handle window close"""
        # Save settings
        self._save_settings()
        
        # Clean up resources
        for tab in self.tabs.values():
            if tab.webview:
                tab.webview = None
        
        window.destroy()
    
    def _save_settings(self):
        """Save browser settings"""
        settings_file = Path.home() / ".config" / "aurora" / "browser_settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
    
    def close_tab(self, tab_id: str):
        """Close a tab"""
        if tab_id not in self.tabs:
            return
        
        tab = self.tabs[tab_id]
        
        # Remove webview from stack
        if tab.webview:
            self.webview_container.remove(tab.webview)
        
        # Remove tab button
        for child in self.tabs_box.get_children():
            if getattr(child, 'tab_id', None) == tab_id:
                self.tabs_box.remove(child)
                break
        
        # Remove from tabs
        del self.tabs[tab_id]
        
        # Clear insights
        if tab_id in self.ai_insights:
            del self.ai_insights[tab_id]
        
        # If this was the active tab, switch to another
        if self.active_tab_id == tab_id:
            if self.tabs:
                # Switch to the last tab
                last_tab_id = list(self.tabs.keys())[-1]
                self.switch_to_tab(last_tab_id)
            else:
                # Create a new tab if no tabs left
                self._create_new_tab()
                self.active_tab_id = None
        
        self.logger.info(f"Closed tab: {tab_id}")
    
    def show(self):
        """Show the browser window"""
        if self.window:
            self.window.show()

# Global browser instance
_aurora_browser = None

def get_aurora_browser() -> AuroraBrowser:
    """Get global Aurora browser instance"""
    global _aurora_browser
    if _aurora_browser is None:
        _aurora_browser = AuroraBrowser()
    return _aurora_browser

def launch_browser():
    """Launch Aurora browser"""
    browser = get_aurora_browser()
    browser.show()
    return browser