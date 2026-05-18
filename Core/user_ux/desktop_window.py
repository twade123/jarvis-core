import sys
import json
from pathlib import Path
import logging
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QProgressBar, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import QUrl, Qt, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt6.QtGui import QIcon

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CustomWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source):
        levels = {
            0: "INFO",
            1: "WARNING",
            2: "ERROR"
        }
        level_str = levels.get(level, "UNKNOWN")
        logger.debug(f"JS {level_str}: {message} (line {line}, source: {source})")

    def certificateError(self, error):
        logger.error(f"Certificate error: {error.errorDescription()}")
        return False

class JarvisDesktop:
    def __init__(self):
        self.config = self.load_config()
        self.app = QApplication(sys.argv)
        self.window = None
        self.web_view = None
        self.loading_label = None
        self.content_loaded = False
        self.load_retries = 0
        self.max_retries = 3
        self.profile = None  # Store profile reference
        
    def load_config(self):
        """Load configuration"""
        config_path = Path(__file__).parent / "config.json"
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded config: {config}")
                return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {
                "frontend_port": 3000,
                "window_width": 1200,
                "window_height": 800,
                "window_title": "Trevor Desktop"
            }

    def create_window(self):
        """Create the desktop window with embedded web view"""
        try:
            # Create main window
            self.window = QMainWindow()
            self.window.setWindowTitle(self.config.get("window_title", "Trevor Desktop"))
            self.window.setGeometry(100, 100, 
                                  self.config.get("window_width", 1200),
                                  self.config.get("window_height", 800))

            # Create central widget and layout
            central_widget = QWidget()
            central_widget.setStyleSheet("background-color: #1f2937;")  # Dark background
            layout = QVBoxLayout(central_widget)
            
            # Create loading label with more detailed status
            self.loading_label = QLabel("Initializing Trevor...")
            self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.loading_label.setStyleSheet("""
                font-size: 24px;
                color: white;
                background-color: transparent;
                padding: 20px;
            """)
            layout.addWidget(self.loading_label)

            # Create web view with custom profile and settings
            self.profile = QWebEngineProfile("trevor_profile")  # Store profile reference
            self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
            
            self.web_view = QWebEngineView()
            page = CustomWebEnginePage(self.profile, self.web_view)
            self.web_view.setPage(page)
            
            # Enable developer tools and JavaScript console
            page.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            page.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            page.settings().setAttribute(QWebEngineSettings.WebAttribute.ErrorPageEnabled, True)
            page.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
            page.settings().setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
            page.settings().setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
            
            self.web_view.hide()  # Hide initially
            layout.addWidget(self.web_view)
            
            # Set up URL and load handlers
            url = QUrl(f'http://localhost:{self.config["frontend_port"]}')
            logger.info(f"Loading URL: {url.toString()}")
            
            def handle_url_changed(url):
                logger.info(f"URL changed to: {url.toString()}")
                # Get the page HTML to see what's actually loaded
                self.web_view.page().toHtml(lambda html: logger.debug(f"Current page HTML: {html[:500]}..."))
            
            def handle_loading_started():
                logger.info("Page loading started")
                self.loading_label.setText("Loading Trevor interface...")
                self.loading_label.show()
                self.web_view.hide()
                # Log the current URL being loaded
                logger.info(f"Loading URL: {self.web_view.url().toString()}")
            
            def handle_load_finished(ok):
                if ok:
                    logger.info("Page load finished, checking content...")
                    # Get both HTML and any JavaScript errors
                    self.web_view.page().toHtml(self.check_content)
                    self.web_view.page().runJavaScript(
                        "console.log('Page loaded, checking for errors...'); "
                        "if (window.lastError) console.error('Last error:', window.lastError);",
                        lambda result: logger.debug(f"JavaScript check result: {result}")
                    )
                else:
                    logger.error("Failed to load page")
                    if self.load_retries < self.max_retries:
                        self.load_retries += 1
                        self.loading_label.setText(f"Load failed, retrying ({self.load_retries}/{self.max_retries})...")
                        QTimer.singleShot(2000, lambda: self.web_view.reload())
                    else:
                        self.loading_label.setText("Failed to load Trevor interface. Check console for errors.")
                        # Try to get any error information
                        self.web_view.page().toHtml(lambda html: logger.error(f"Failed page content: {html[:500]}..."))
            
            # Connect all signals
            self.web_view.urlChanged.connect(handle_url_changed)
            self.web_view.loadStarted.connect(handle_loading_started)
            self.web_view.loadProgress.connect(self.handle_loading_progress)
            self.web_view.loadFinished.connect(handle_load_finished)
            
            # Set up close handler
            self.window.closeEvent = self.handle_close
            
            # Load the URL
            self.web_view.setUrl(url)
            
            # Set as central widget
            self.window.setCentralWidget(central_widget)
            
            # Show window and bring to front
            self.window.show()
            self.window.raise_()
            self.window.activateWindow()
            
            # Keep a reference to prevent garbage collection
            self.central_widget = central_widget
            self.layout = layout
            
            # Set up a timer to check loading status
            QTimer.singleShot(30000, self.check_loading_timeout)
            
        except Exception as e:
            logger.error(f"Error creating window: {e}", exc_info=True)
            sys.exit(1)

    def handle_close(self, event):
        """Handle window close event"""
        try:
            logger.info("Window closing, cleaning up...")
            if self.web_view:
                self.web_view.setPage(None)  # Remove page from web view
            if hasattr(self, 'profile') and self.profile:
                self.profile.deleteLater()  # Schedule profile for deletion
            event.accept()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            event.accept()

    def check_loading_timeout(self):
        """Check if loading has timed out"""
        if not self.content_loaded:
            logger.error("Loading timed out after 30 seconds")
            self.loading_label.setText("Loading timed out. Check console for errors.")
            # Execute JavaScript to get any errors
            self.web_view.page().runJavaScript(
                "console.error('Loading timed out. Last error:', window.lastError || 'No error recorded');",
                lambda result: logger.error(f"JavaScript error check: {result}")
            )

    def check_content(self, html):
        """Check if the loaded content is valid"""
        logger.debug(f"Checking content, length: {len(html)}")
        try:
            if len(html) > 0:  # First check if we have any content
                logger.info("Content received, checking for root element...")
                if "<div id=\"root\">" in html:
                    logger.info("Root element found, checking if content is loaded...")
                    # Additional check for actual content
                    if len(html) > 1000:  # Basic check to ensure we have more than just the basic HTML structure
                        if not self.content_loaded:
                            logger.info("Valid content detected, showing web view")
                            self.content_loaded = True
                            self.loading_label.hide()
                            self.web_view.show()
                            # Add JavaScript error handler
                            self.web_view.page().runJavaScript("""
                                window.onerror = function(msg, url, line) {
                                    window.lastError = msg + ' at ' + url + ':' + line;
                                    console.error('Error:', msg, 'at', url, ':', line);
                                    return false;
                                };
                            """)
                            return
                    else:
                        logger.warning("Content seems too short, might not be fully loaded")
                else:
                    logger.warning("Root element not found in content")
            else:
                logger.warning("Received empty content")
            
            # If we get here, content wasn't valid
            if self.load_retries < self.max_retries:
                self.load_retries += 1
                logger.info(f"Retrying load ({self.load_retries}/{self.max_retries})")
                self.loading_label.setText(f"Loading Trevor interface... Attempt {self.load_retries + 1}/{self.max_retries}")
                QTimer.singleShot(2000, lambda: self.web_view.reload())
            else:
                logger.error("Max retries reached, content still not valid")
                self.loading_label.setText("Failed to load Trevor interface. Please check the console for errors.")
                
        except Exception as e:
            logger.error(f"Error checking content: {e}", exc_info=True)
            self.loading_label.setText("Error checking content. Please check the console for details.")

    def handle_loading_progress(self, progress):
        """Handle page loading progress"""
        logger.info(f"Loading progress: {progress}%")
        self.loading_label.setText(f"Loading Trevor interface... {progress}%")

    def run(self):
        """Start the desktop application"""
        self.create_window()
        # Start the Qt event loop and keep it running
        return self.app.exec()

def main():
    app = JarvisDesktop()
    app.run()

if __name__ == "__main__":
    main() 