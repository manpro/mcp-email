from flask import Flask, render_template_string, jsonify
import json
import os

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Dashboard</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🚀</text></svg>">
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- DOWNGRADED: Using AlpineJS 3.10.5 to avoid .after() bugs -->
    <script src="https://unpkg.com/alpinejs@3.10.5/dist/cdn.min.js" defer></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
        }
    </script>
    <style>
        .project-card {
            transition: all 0.2s ease-in-out;
        }
        .project-card:hover {
            transform: translateY(-2px);
        }
        .theme-toggle {
            transition: all 0.2s ease-in-out;
        }
        /* Hide elements until Alpine.js loads to prevent flash */
        [x-cloak] { display: none !important; }
    </style>
</head>
<body class="bg-gray-50 dark:bg-gray-900 min-h-screen transition-colors duration-200">
    <div class="container mx-auto px-4 py-8" x-data="projectDashboard()" x-init="init()">
        <!-- Header -->
        <div class="mb-8">
            <div class="flex justify-between items-start mb-4">
                <div>
                    <h1 class="text-4xl font-bold text-gray-800 dark:text-gray-100 mb-2">🚀 Project Dashboard</h1>
                    <p class="text-gray-600 dark:text-gray-400">Översikt över alla mjukvaruprojekt på servern</p>
                </div>
                <!-- Dark/Light Theme Toggle Button -->
                <button @click="toggleTheme()" 
                        class="theme-toggle p-2 rounded-lg bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300"
                        title="Växla mellan ljust och mörkt tema">
                    <span x-show="!darkMode">🌙</span>
                    <span x-show="darkMode">☀️</span>
                </button>
            </div>
            <div class="mt-4">
                <span class="text-sm text-gray-500 dark:text-gray-400">
                    Totalt: <span x-text="safeProjectCount()"></span> projekt
                </span>
            </div>
        </div>

        <!-- Search -->
        <div class="mb-6">
            <input x-model="searchText" 
                   type="text" 
                   placeholder="Sök projekt..." 
                   class="w-full max-w-md px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors">
        </div>

        <!-- Filter Buttons -->
        <div class="mb-6">
            <div class="flex flex-wrap gap-2">
                <!-- FIXED: Always show all projects - ignore filter button state -->
                <button @click="showAllProjects()" 
                        :class="true ? 'bg-blue-500 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'"
                        class="px-3 py-1 rounded-full text-sm transition-colors">
                    Alla (<span x-text="safeProjectCount()"></span>)
                </button>
                <!-- SIMPLIFIED: Basic type buttons without complex counting -->
                <template x-for="type in getProjectTypesSimple()" x-bind:key="type">
                    <button @click="filterByType(type)" 
                            class="px-3 py-1 rounded-full text-sm transition-colors bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
                            x-text="type">
                    </button>
                </template>
            </div>
        </div>

        <!-- Loading state -->
        <div x-show="loading" class="text-center py-8">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
            <p class="mt-2 text-gray-600 dark:text-gray-400">Laddar projekt...</p>
        </div>

        <!-- Results count -->
        <div x-show="!loading" class="mb-4">
            <p class="text-sm text-gray-600 dark:text-gray-400">
                Visar <span x-text="getDisplayedProjectCount()"></span> av <span x-text="safeProjectCount()"></span> projekt
            </p>
        </div>

        <!-- Project Grid - SIMPLIFIED APPROACH -->
        <div x-show="!loading && hasProjectsToShow()" 
             class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            <!-- DRASTICALLY SIMPLIFIED: Use simple index-based keys -->
            <template x-for="(project, index) in getDisplayProjects()" x-bind:key="'proj-' + index">
                <div class="project-card bg-white dark:bg-gray-800 rounded-lg shadow-md dark:shadow-gray-900/30 p-6 hover:shadow-lg dark:hover:shadow-gray-900/50 transition-colors">
                    <!-- Project Header -->
                    <div class="flex items-start justify-between mb-3">
                        <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100 truncate flex-1" 
                            x-text="getProjectName(project)"></h3>
                        <div class="ml-2">
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                                  x-bind:class="getTypeColor(getProjectType(project))"
                                  x-text="getProjectType(project)">
                            </span>
                        </div>
                    </div>

                    <!-- Description -->
                    <p class="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-3" 
                       x-text="getProjectDescription(project)"></p>

                    <!-- Indicators - SIMPLIFIED -->
                    <div class="mb-4" x-show="hasIndicators(project)">
                        <div class="flex flex-wrap gap-1">
                            <!-- SAFE: Use simple slice without complex logic -->
                            <template x-for="(indicator, idx) in getProjectIndicators(project)" x-bind:key="'ind-' + index + '-' + idx">
                                <span class="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                                      x-text="indicator">
                                </span>
                            </template>
                        </div>
                    </div>

                    <!-- Actions -->
                    <div class="flex space-x-2">
                        <button @click="openPath(getProjectPath(project))" 
                                class="flex-1 bg-blue-500 hover:bg-blue-600 text-white text-sm py-2 px-3 rounded transition-colors">
                            📁 Öppna
                        </button>
                        <button x-show="hasDocumentation(project)" 
                                @click="openDocumentation(project)"
                                class="bg-green-500 hover:bg-green-600 text-white text-sm py-2 px-3 rounded transition-colors">
                            🌐
                        </button>
                        <button @click="showDetails(project)" 
                                class="bg-gray-500 hover:bg-gray-600 text-white text-sm py-2 px-3 rounded transition-colors">
                            ℹ️
                        </button>
                    </div>
                </div>
            </template>
        </div>

        <!-- No results -->
        <div x-show="!loading && !hasProjectsToShow()" class="text-center py-8">
            <p class="text-gray-600 dark:text-gray-400">Inga projekt hittades.</p>
        </div>

        <!-- Modal - SIMPLIFIED -->
        <div x-show="showModal" 
             x-cloak
             class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
             @click.self="showModal = false">
            <div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-2xl w-full max-h-96 overflow-y-auto mx-4">
                <div class="flex justify-between items-start mb-4">
                    <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100" 
                        x-text="getProjectName(selectedProject)"></h2>
                    <button @click="showModal = false" class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">✕</button>
                </div>
                <div x-show="selectedProject">
                    <p class="text-gray-600 dark:text-gray-400 mb-3">
                        <strong>Sökväg:</strong> 
                        <code x-text="getProjectPath(selectedProject)" class="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded"></code>
                    </p>
                    <p class="text-gray-600 dark:text-gray-400 mb-3">
                        <strong>Typ:</strong> 
                        <span x-text="getProjectType(selectedProject)"></span>
                    </p>
                    <p class="text-gray-600 dark:text-gray-400 mb-3">
                        <strong>Beskrivning:</strong> 
                        <span x-text="getProjectDescription(selectedProject)"></span>
                    </p>
                </div>
            </div>
        </div>
    </div>

    <script>
        function projectDashboard() {
            return {
                // STATE VARIABLES
                projects: [],
                displayProjects: [], // CRITICAL: Separate display list to avoid .after() bugs
                loading: true,
                searchText: '',
                currentFilter: 'all', // SIMPLIFIED: Just track current filter
                showModal: false,
                selectedProject: null,
                darkMode: false,

                // SAFE PROJECT ACCESS METHODS

                getProjectName(project) {
                    if (!project) return 'Namnlöst projekt';
                    return project.name || project.title || 'Namnlöst projekt';
                },

                getProjectType(project) {
                    if (!project) return 'Okänd';
                    return project.type || 'Okänd';
                },

                getProjectDescription(project) {
                    if (!project) return 'Ingen beskrivning tillgänglig';
                    return project.description || 'Ingen beskrivning tillgänglig';
                },

                getProjectPath(project) {
                    if (!project) return '';
                    return project.path || '';
                },

                getProjectIndicators(project) {
                    if (!project || !Array.isArray(project.indicators)) return [];
                    return project.indicators.filter(ind => ind && ind.trim()).slice(0, 4);
                },

                hasIndicators(project) {
                    return this.getProjectIndicators(project).length > 0;
                },

                hasDocumentation(project) {
                    return project && project.documentation && typeof project.documentation === 'string' && project.documentation.trim() !== '';
                },

                // SAFE COUNTING METHODS

                safeProjectCount() {
                    return Array.isArray(this.projects) ? this.projects.length : 0;
                },

                getDisplayedProjectCount() {
                    return Array.isArray(this.displayProjects) ? this.displayProjects.length : 0;
                },

                hasProjectsToShow() {
                    return Array.isArray(this.displayProjects) && this.displayProjects.length > 0;
                },

                // DISPLAY METHODS

                getDisplayProjects() {
                    return this.displayProjects || [];
                },

                getProjectTypesSimple() {
                    if (!Array.isArray(this.projects)) return [];
                    try {
                        const types = [...new Set(this.projects
                            .filter(p => p && p.type)
                            .map(p => p.type)
                        )].sort();
                        return types.slice(0, 8); // Limit to prevent DOM issues
                    } catch (error) {
                        console.warn('Error getting project types:', error);
                        return [];
                    }
                },

                // FILTERING METHODS - SIMPLIFIED TO AVOID .after() ERRORS

                showAllProjects() {
                    console.log('Showing all projects');
                    this.currentFilter = 'all';
                    this.updateDisplayProjects();
                },

                filterByType(type) {
                    console.log('Filtering by type:', type);
                    this.currentFilter = type;
                    this.updateDisplayProjects();
                },

                updateDisplayProjects() {
                    if (!Array.isArray(this.projects)) {
                        this.displayProjects = [];
                        return;
                    }

                    try {
                        let filtered = this.projects.filter(project => {
                            if (!project) return false;
                            
                            // Search filter
                            const searchTerm = (this.searchText || '').toLowerCase();
                            if (searchTerm) {
                                const name = (project.name || '').toLowerCase();
                                const description = (project.description || '').toLowerCase();
                                if (!name.includes(searchTerm) && !description.includes(searchTerm)) {
                                    return false;
                                }
                            }
                            
                            // Type filter
                            if (this.currentFilter !== 'all') {
                                return project.type === this.currentFilter;
                            }
                            
                            return true;
                        });

                        // CRITICAL: Create new array to break any Alpine references
                        this.displayProjects = [...filtered];
                        console.log('Display projects updated:', this.displayProjects.length);
                        
                    } catch (error) {
                        console.error('Error updating display projects:', error);
                        this.displayProjects = [];
                    }
                },

                // COLOR METHODS

                getTypeColor(type) {
                    const colors = {
                        'Python': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
                        'Node.js/JavaScript': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
                        'Docker': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
                        'Java': 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
                        'Go': 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
                        'Rust': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
                        'Web/HTML': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
                        'Git Repository': 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
                        'Documentation Platform': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
                        'External Documentation Server': 'bg-violet-100 text-violet-800 dark:bg-violet-900 dark:text-violet-200',
                        'Collaborative Markdown Editor': 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
                        'Diagram Generation Service': 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200',
                        'Full-Stack AI Application': 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
                        'Unknown': 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                    };
                    return colors[type] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400';
                },

                // THEME METHODS

                toggleTheme() {
                    this.darkMode = !this.darkMode;
                    localStorage.setItem('darkMode', this.darkMode.toString());
                    this.applyTheme();
                },

                applyTheme() {
                    if (this.darkMode) {
                        document.documentElement.classList.add('dark');
                    } else {
                        document.documentElement.classList.remove('dark');
                    }
                },

                initializeTheme() {
                    const savedTheme = localStorage.getItem('darkMode');
                    if (savedTheme !== null) {
                        this.darkMode = savedTheme === 'true';
                    } else {
                        this.darkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                    }
                    this.applyTheme();
                },

                // ACTION METHODS

                openPath(path) {
                    if (!path || path.trim() === '') {
                        alert('Ingen sökväg tillgänglig');
                        return;
                    }
                    try {
                        navigator.clipboard.writeText(path).then(() => {
                            alert('Sökväg kopierad till urklipp: ' + path);
                        }).catch(() => {
                            alert('Sökväg: ' + path);
                        });
                    } catch (error) {
                        alert('Sökväg: ' + path);
                    }
                },

                openDocumentation(project) {
                    if (this.hasDocumentation(project)) {
                        window.open(project.documentation, '_blank');
                    }
                },

                showDetails(project) {
                    if (project) {
                        this.selectedProject = project;
                        this.showModal = true;
                    }
                },

                // DATA LOADING

                async loadProjects() {
                    try {
                        console.log('Loading projects...');
                        const response = await fetch('/api/projects');
                        
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        
                        const data = await response.json();
                        console.log('Projects loaded:', Array.isArray(data) ? data.length : 'invalid data', 'projects');
                        
                        if (!Array.isArray(data)) {
                            throw new Error('API did not return an array');
                        }
                        
                        // CRITICAL: Clean data to prevent undefined errors
                        this.projects = data.filter(project => {
                            if (!project) {
                                console.warn('Skipping null project');
                                return false;
                            }
                            
                            if (!project.name && !project.path) {
                                console.warn('Skipping project without name or path');
                                return false;
                            }
                            
                            // Ensure arrays are valid
                            if (project.indicators && !Array.isArray(project.indicators)) {
                                project.indicators = [];
                            }
                            
                            if (project.ports && !Array.isArray(project.ports)) {
                                project.ports = [];
                            }
                            
                            return true;
                        });
                        
                        console.log('Valid projects loaded:', this.projects.length);
                        
                        // CRITICAL: Always show all projects by default
                        this.currentFilter = 'all';
                        this.updateDisplayProjects();
                        
                    } catch (error) {
                        console.error('Error loading projects:', error);
                        this.projects = [];
                        this.displayProjects = [];
                        alert('Fel vid laddning av projekt: ' + error.message);
                    } finally {
                        this.loading = false;
                    }
                },

                // WATCHERS - Use simple watchers to update display

                watchSearch() {
                    this.$watch('searchText', () => {
                        setTimeout(() => this.updateDisplayProjects(), 100);
                    });
                },

                // INITIALIZATION

                init() {
                    console.log('Project dashboard initialized');
                    
                    // Initialize theme
                    this.initializeTheme();
                    
                    // Set up search watcher
                    this.watchSearch();
                    
                    // Load projects
                    this.loadProjects();
                    
                    // Listen for system theme changes
                    if (window.matchMedia) {
                        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                            if (localStorage.getItem('darkMode') === null) {
                                this.darkMode = e.matches;
                                this.applyTheme();
                            }
                        });
                    }
                }
            };
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/projects')
def api_projects():
    """API endpoint to get all projects as JSON."""
    try:
        projects_file = '/home/micke/claude-env/project_dashboard/projects.json'
        if os.path.exists(projects_file):
            with open(projects_file, 'r') as f:
                projects = json.load(f)
            return jsonify(projects)
        else:
            return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scan')
def api_scan():
    """API endpoint to rescan for projects."""
    try:
        import subprocess
        result = subprocess.run(['python3', '/home/micke/claude-env/project_dashboard/scan_projects.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return jsonify({'success': True, 'message': 'Scan completed successfully'})
        else:
            return jsonify({'success': False, 'error': result.stderr}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Project Dashboard on http://localhost:6888")
    print("📁 Serving projects from: /home/micke/project_dashboard/projects.json")
    app.run(host='0.0.0.0', port=6888, debug=True)