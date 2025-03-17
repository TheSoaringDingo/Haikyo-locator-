"""
Module for the user interface of the Haikyo Locator application.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import time
from scraper import HaikyoScraper
from kml_generator import KMLGenerator

class HaikyoApplication:
    """Main UI class for the Haikyo Locator application."""
    
    def __init__(self, root):
        """
        Initialize the application UI.
        
        Args:
            root (tk.Tk): The root Tkinter window.
        """
        self.root = root
        self.scraper = HaikyoScraper()
        self.kml_generator = KMLGenerator()
        self.locations = []
        self.search_thread = None
        self.scrape_thread = None
        self.generate_kml_thread = None
        
        # Set up the UI
        self._create_widgets()
        self._setup_layout()
    
    def _create_widgets(self):
        """Create all UI widgets."""
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        
        # Search section
        self.search_frame = ttk.LabelFrame(self.main_frame, text="Search", padding="10")
        self.search_label = ttk.Label(self.search_frame, text="Search Term:")
        self.search_entry = ttk.Entry(self.search_frame, width=40)
        self.search_button = ttk.Button(self.search_frame, text="Search", command=self._start_search)
        
        # Results section
        self.results_frame = ttk.LabelFrame(self.main_frame, text="Search Results", padding="10")
        
        # Create a frame for the treeview and scrollbar
        self.tree_frame = ttk.Frame(self.results_frame)
        
        # Create treeview widget with scrollbars
        self.tree_columns = ("title", "url", "coordinates")
        self.tree = ttk.Treeview(self.tree_frame, columns=self.tree_columns, show="headings", selectmode="extended")
        
        # Set column headings
        self.tree.heading("title", text="Location Name")
        self.tree.heading("url", text="URL")
        self.tree.heading("coordinates", text="Coordinates")
        
        # Set column widths
        self.tree.column("title", width=200, minwidth=150)
        self.tree.column("url", width=300, minwidth=200)
        self.tree.column("coordinates", width=150, minwidth=100)
        
        # Add scrollbars to the treeview
        self.tree_yscroll = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_yscroll.set)
        
        # Actions section
        self.actions_frame = ttk.Frame(self.results_frame)
        self.select_all_button = ttk.Button(self.actions_frame, text="Select All", command=self._select_all)
        self.select_none_button = ttk.Button(self.actions_frame, text="Select None", command=self._select_none)
        self.scrape_button = ttk.Button(self.actions_frame, text="Scrape Selected", command=self._start_scraping)
        self.generate_kml_button = ttk.Button(self.actions_frame, text="Generate KML", command=self._start_generate_kml)
        
        # Details section
        self.details_frame = ttk.LabelFrame(self.main_frame, text="Location Details", padding="10")
        self.details_text = scrolledtext.ScrolledText(self.details_frame, wrap=tk.WORD, width=70, height=15)
        self.details_text.config(state=tk.DISABLED)
        
        # Progress section
        self.progress_frame = ttk.LabelFrame(self.main_frame, text="Progress", padding="10")
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.status_label = ttk.Label(self.progress_frame, text="Ready")
        
        # Bind treeview selection event
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        
    def _setup_layout(self):
        """Arrange all widgets using the grid layout manager."""
        # Main frame
        self.main_frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Search section
        self.search_frame.grid(column=0, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.search_label.grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.search_entry.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.search_button.grid(column=2, row=0, sticky=tk.E, padx=5, pady=5)
        
        # Results section
        self.results_frame.grid(column=0, row=1, sticky=(tk.N, tk.W, tk.E, tk.S), padx=5, pady=5)
        
        # Tree frame
        self.tree_frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S), padx=5, pady=5)
        self.tree.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.tree_yscroll.grid(column=1, row=0, sticky=(tk.N, tk.S))
        
        # Actions section
        self.actions_frame.grid(column=0, row=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.select_all_button.grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.select_none_button.grid(column=1, row=0, sticky=tk.W, padx=5, pady=5)
        self.scrape_button.grid(column=2, row=0, sticky=tk.E, padx=5, pady=5)
        self.generate_kml_button.grid(column=3, row=0, sticky=tk.E, padx=5, pady=5)
        
        # Details section
        self.details_frame.grid(column=0, row=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.details_text.grid(column=0, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Progress section
        self.progress_frame.grid(column=0, row=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.progress_bar.grid(column=0, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.status_label.grid(column=0, row=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Configure weights for resizing
        self.main_frame.columnconfigure(0, weight=1)
        self.search_frame.columnconfigure(1, weight=1)
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)
        self.tree_frame.columnconfigure(0, weight=1)
        self.tree_frame.rowconfigure(0, weight=1)
        self.details_frame.columnconfigure(0, weight=1)
        self.progress_frame.columnconfigure(0, weight=1)
    
    def _start_search(self):
        """Start the search operation in a separate thread."""
        search_term = self.search_entry.get().strip()
        if not search_term:
            messagebox.showwarning("Warning", "Please enter a search term.")
            return
        
        # Disable the search button to prevent multiple searches
        self.search_button.config(state=tk.DISABLED)
        
        # Clear previous results
        self._clear_results()
        
        # Start the search in a separate thread
        self.search_thread = threading.Thread(target=self._search_task, args=(search_term,))
        self.search_thread.daemon = True
        self.search_thread.start()
    
    def _search_task(self, search_term):
        """
        Perform the search task in a background thread.
        
        Args:
            search_term (str): The search term to use.
        """
        try:
            # Update status
            self._update_status(0, "Searching for locations...")
            
            # Perform the search
            urls = self.scraper.search_locations(search_term, self._update_status)
            
            # Get basic details for each URL
            for i, url in enumerate(urls):
                progress = (i + 1) / len(urls) * 100
                self._update_status(progress, f"Processing search result {i+1} of {len(urls)}")
                
                # Extract basic info from URL
                title = url.split('/')[-1].replace('-', ' ').title()
                
                # Add to the treeview
                self._add_to_treeview(title, url, "Click 'Scrape Selected' to get coordinates")
                
                # Add to locations list
                self.locations.append({
                    'title': title,
                    'url': url,
                    'coordinates': None,
                    'description': "",
                    'images': []
                })
                
                # Pause briefly to allow UI updates
                time.sleep(0.1)
            
            # Update status
            if len(urls) > 0:
                self._update_status(100, f"Found {len(urls)} locations")
            else:
                self._update_status(100, "No locations found. Try a different search term.")
        
        except Exception as e:
            self._update_status(0, f"Error during search: {str(e)}")
        
        finally:
            # Enable the search button
            self.root.after(0, lambda: self.search_button.config(state=tk.NORMAL))
    
    def _start_scraping(self):
        """Start scraping selected locations in a separate thread."""
        # Get selected items
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select at least one location to scrape.")
            return
        
        # Disable buttons during scraping
        self.scrape_button.config(state=tk.DISABLED)
        self.search_button.config(state=tk.DISABLED)
        
        # Start the scraping in a separate thread
        self.scrape_thread = threading.Thread(target=self._scrape_task, args=(selected_items,))
        self.scrape_thread.daemon = True
        self.scrape_thread.start()
    
    def _scrape_task(self, selected_items):
        """
        Perform the scraping task in a background thread.
        
        Args:
            selected_items (list): List of selected tree item IDs.
        """
        try:
            # Update status
            self._update_status(0, "Scraping selected locations...")
            
            selected_urls = []
            selected_indices = []
            
            # Get URLs for selected items
            for item_id in selected_items:
                item_values = self.tree.item(item_id, 'values')
                url = item_values[1]  # URL is in the second column
                
                # Find the corresponding index in the locations list
                for i, location in enumerate(self.locations):
                    if location['url'] == url:
                        selected_urls.append(url)
                        selected_indices.append(i)
                        break
            
            # Scrape location details
            scraped_locations = self.scraper.scrape_batch(selected_urls, self._update_status)
            
            # Update locations list and treeview with scraped data
            for i, location_data in enumerate(scraped_locations):
                index = selected_indices[i]
                self.locations[index] = location_data
                
                # Update the treeview
                item_id = selected_items[i]
                coords_text = f"{location_data['coordinates']['lat']}, {location_data['coordinates']['lng']}"
                self.tree.item(item_id, values=(location_data['title'], location_data['url'], coords_text))
            
            # Update status
            self._update_status(100, f"Scraped {len(scraped_locations)} locations")
        
        except Exception as e:
            self._update_status(0, f"Error during scraping: {str(e)}")
        
        finally:
            # Enable buttons
            self.root.after(0, lambda: self.scrape_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.search_button.config(state=tk.NORMAL))
    
    def _start_generate_kml(self):
        """Start generating KML file in a separate thread."""
        # Check if we have locations with coordinates
        valid_locations = [loc for loc in self.locations if loc['coordinates'] and 
                          (loc['coordinates']['lat'] != 0 or loc['coordinates']['lng'] != 0)]
        
        if not valid_locations:
            messagebox.showwarning("Warning", "No locations with valid coordinates to export. Please scrape locations first.")
            return
        
        # Ask for output file location
        output_file = filedialog.asksaveasfilename(
            defaultextension=".kml",
            filetypes=[("KML files", "*.kml"), ("All files", "*.*")],
            title="Save KML File"
        )
        
        if not output_file:
            return  # User cancelled
        
        # Disable button during KML generation
        self.generate_kml_button.config(state=tk.DISABLED)
        
        # Start the KML generation in a separate thread
        self.generate_kml_thread = threading.Thread(target=self._generate_kml_task, args=(output_file,))
        self.generate_kml_thread.daemon = True
        self.generate_kml_thread.start()
    
    def _generate_kml_task(self, output_file):
        """
        Generate KML file in a background thread.
        
        Args:
            output_file (str): Path to save the KML file.
        """
        try:
            # Update status
            self._update_status(0, "Generating KML file...")
            
            # Generate KML file
            success = self.kml_generator.generate_kml(self.locations, output_file, self._update_status)
            
            if success:
                self._update_status(100, f"KML file generated successfully: {os.path.basename(output_file)}")
                self.root.after(0, lambda: messagebox.showinfo("Success", 
                                                             f"KML file generated successfully.\n\nFile: {output_file}"))
            else:
                self._update_status(0, "Failed to generate KML file")
        
        except Exception as e:
            self._update_status(0, f"Error generating KML file: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to generate KML file: {str(e)}"))
        
        finally:
            # Enable button
            self.root.after(0, lambda: self.generate_kml_button.config(state=tk.NORMAL))
    
    def _update_status(self, progress, message):
        """
        Update the status display from any thread.
        
        Args:
            progress (float): Progress value (0-100)
            message (str): Status message
        """
        self.root.after(0, lambda: self._update_status_ui(progress, message))
    
    def _update_status_ui(self, progress, message):
        """
        Update the status UI components.
        
        Args:
            progress (float): Progress value (0-100)
            message (str): Status message
        """
        self.progress_bar['value'] = progress
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def _add_to_treeview(self, title, url, coordinates):
        """
        Add an item to the treeview.
        
        Args:
            title (str): Location title
            url (str): Location URL
            coordinates (str): Coordinates as string
        """
        self.tree.insert('', tk.END, values=(title, url, coordinates))
    
    def _clear_results(self):
        """Clear all results from the treeview and locations list."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.locations = []
        self._clear_details()
    
    def _select_all(self):
        """Select all items in the treeview."""
        for item in self.tree.get_children():
            self.tree.selection_add(item)
    
    def _select_none(self):
        """Deselect all items in the treeview."""
        for item in self.tree.get_children():
            self.tree.selection_remove(item)
    
    def _on_tree_select(self, event):
        """
        Handle treeview selection event.
        
        Args:
            event: The Tkinter event object
        """
        selected_items = self.tree.selection()
        if selected_items:
            item_values = self.tree.item(selected_items[0], 'values')
            url = item_values[1]  # URL is in the second column
            
            # Find the corresponding location
            for location in self.locations:
                if location['url'] == url:
                    self._show_details(location)
                    break
    
    def _show_details(self, location):
        """
        Show location details in the details text area.
        
        Args:
            location (dict): Location dictionary with details
        """
        # Enable editing
        self.details_text.config(state=tk.NORMAL)
        
        # Clear previous content
        self.details_text.delete(1.0, tk.END)
        
        # Add details
        self.details_text.insert(tk.END, f"Title: {location['title']}\n\n")
        self.details_text.insert(tk.END, f"URL: {location['url']}\n\n")
        
        if location['coordinates']:
            coords = location['coordinates']
            self.details_text.insert(tk.END, f"Coordinates: {coords['lat']}, {coords['lng']}\n\n")
        else:
            self.details_text.insert(tk.END, "Coordinates: Not available\n\n")
        
        if location['description']:
            self.details_text.insert(tk.END, f"Description:\n{location['description'][:500]}{'...' if len(location['description']) > 500 else ''}\n\n")
        
        if location['images']:
            self.details_text.insert(tk.END, f"Images: {len(location['images'])} images available\n")
            for i, img_url in enumerate(location['images'][:5]):
                self.details_text.insert(tk.END, f"{i+1}. {img_url}\n")
        
        # Disable editing
        self.details_text.config(state=tk.DISABLED)
    
    def _clear_details(self):
        """Clear the details text area."""
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.config(state=tk.DISABLED)
