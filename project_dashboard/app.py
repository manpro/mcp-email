#!/usr/bin/env python3

from flask import Flask, jsonify, render_template_string
import json
import os

app = Flask(__name__)

# HTML template with TailwindCSS
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <style>
        .project-card {
            transition: all 0.2s ease-in-out;
        }
        .project-card:hover {
            transform: translateY(-2px);
        }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8" x-data="projectDashboard()">
        <!-- Header -->
        <div class="mb-8">
            <h1 class="text-4xl font-bold text-gray-800 mb-2">🚀 Project Dashboard</h1>
            <p class="text-gray-600">Översikt över alla mjukvaruprojekt på servern</p>
            <div class="mt-4 flex items-center space-x-4">
                <span class="text-sm text-gray-500">Totalt: <span x-text="projects.length"></span> projekt</span>
                <div class="flex space-x-2">
                    <button @click="selectedType = 'all'" 
                            :class="selectedType === 'all' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700'"
                            class="px-3 py-1 rounded-full text-sm transition-colors">
                        Alla
                    </button>
                    <template x-for="type in projectTypes" :key="type">
                        <button @click="selectedType = type" 
                                :class="selectedType === type ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700'"
                                class="px-3 py-1 rounded-full text-sm transition-colors"
                                x-text="type">
                        </button>
                    </template>
                </div>
            </div>
        </div>

        <!-- Search -->
        <div class="mb-6">
            <input x-model="searchTerm" 
                   type="text" 
                   placeholder="Sök projekt..." 
                   class="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
        </div>

        <!-- Loading state -->
        <div x-show="loading" class="text-center py-8">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
            <p class="mt-2 text-gray-600">Laddar projekt...</p>
        </div>

        <!-- Project Grid -->
        <div x-show="!loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            <template x-for="project in filteredProjects" :key="project.path">
                <div class="project-card bg-white rounded-lg shadow-md p-6 hover:shadow-lg">
                    <!-- Project Header -->
                    <div class="flex items-start justify-between mb-3">
                        <h3 class="text-lg font-semibold text-gray-800 truncate flex-1" x-text="project.name"></h3>
                        <div class="ml-2">
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                                  :class="getTypeColor(project.type)"
                                  x-text="project.type">
                            </span>
                        </div>
                    </div>

                    <!-- Description -->
                    <p class="text-gray-600 text-sm mb-4 line-clamp-3" x-text="project.description"></p>

                    <!-- Indicators -->
                    <div class="mb-4">
                        <div class="flex flex-wrap gap-1">
                            <template x-for="indicator in project.indicators.slice(0, 4)" :key="indicator">
                                <span class="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 text-gray-700"
                                      x-text="indicator">
                                </span>
                            </template>
                            <span x-show="project.indicators.length > 4" 
                                  class="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 text-gray-700"
                                  x-text="'+' + (project.indicators.length - 4)">
                            </span>
                        </div>
                    </div>

                    <!-- Actions -->
                    <div class="flex space-x-2">
                        <button @click="openPath(project.path)" 
                                class="flex-1 bg-blue-500 hover:bg-blue-600 text-white text-sm py-2 px-3 rounded transition-colors">
                            📁 Öppna
                        </button>
                        <button @click="showDetails(project)" 
                                class="bg-gray-500 hover:bg-gray-600 text-white text-sm py-2 px-3 rounded transition-colors">
                            ℹ️
                        </button>
                    </div>
                </div>
            </template>
        </div>

        <!-- Empty state -->
        <div x-show="!loading && filteredProjects.length === 0" class="text-center py-12">
            <div class="text-6xl mb-4">📂</div>
            <h3 class="text-xl font-semibold text-gray-700 mb-2">Inga projekt hittades</h3>
            <p class="text-gray-500">Prova att ändra dina sökkriterier eller filter.</p>
        </div>

        <!-- Details Modal -->
        <div x-show="showModal" 
             x-transition:enter="transition ease-out duration-300"
             x-transition:enter-start="opacity-0"
             x-transition:enter-end="opacity-100"
             x-transition:leave="transition ease-in duration-200"
             x-transition:leave-start="opacity-100"
             x-transition:leave-end="opacity-0"
             class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div x-show="showModal"
                 x-transition:enter="transition ease-out duration-300"
                 x-transition:enter-start="opacity-0 transform scale-95"
                 x-transition:enter-end="opacity-100 transform scale-100"
                 x-transition:leave="transition ease-in duration-200"
                 x-transition:leave-start="opacity-100 transform scale-100"
                 x-transition:leave-end="opacity-0 transform scale-95"
                 class="bg-white rounded-lg p-6 max-w-2xl w-full max-h-96 overflow-y-auto">
                <div class="flex justify-between items-start mb-4">
                    <h2 class="text-xl font-bold text-gray-800" x-text="selectedProject?.name"></h2>
                    <button @click="showModal = false" class="text-gray-500 hover:text-gray-700">✕</button>
                </div>
                <div x-show="selectedProject">
                    <p class="text-gray-600 mb-3"><strong>Sökväg:</strong> <code x-text="selectedProject?.path" class="bg-gray-100 px-2 py-1 rounded"></code></p>
                    <p class="text-gray-600 mb-3"><strong>Typ:</strong> <span x-text="selectedProject?.type"></span></p>
                    <p class="text-gray-600 mb-3"><strong>Beskrivning:</strong> <span x-text="selectedProject?.description"></span></p>
                    <p class="text-gray-600 mb-3"><strong>Indikatorer:</strong></p>
                    <div class="flex flex-wrap gap-2">
                        <template x-for="indicator in selectedProject?.indicators" :key="indicator">
                            <span class="inline-flex items-center px-2 py-1 rounded text-sm bg-blue-100 text-blue-800"
                                  x-text="indicator">
                            </span>
                        </template>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function projectDashboard() {
            return {
                projects: [],
                loading: true,
                searchTerm: '',
                selectedType: 'all',
                showModal: false,
                selectedProject: null,

                get projectTypes() {
                    const types = [...new Set(this.projects.map(p => p.type))].sort();
                    return types;
                },

                get filteredProjects() {
                    return this.projects.filter(project => {
                        const matchesSearch = project.name.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
                                            project.description.toLowerCase().includes(this.searchTerm.toLowerCase());
                        const matchesType = this.selectedType === 'all' || project.type === this.selectedType;
                        return matchesSearch && matchesType;
                    });
                },

                getTypeColor(type) {
                    const colors = {
                        'Python': 'bg-green-100 text-green-800',
                        'Node.js/JavaScript': 'bg-yellow-100 text-yellow-800',
                        'Docker': 'bg-blue-100 text-blue-800',
                        'Java': 'bg-orange-100 text-orange-800',
                        'Go': 'bg-cyan-100 text-cyan-800',
                        'Rust': 'bg-red-100 text-red-800',
                        'Web/HTML': 'bg-purple-100 text-purple-800',
                        'Git Repository': 'bg-gray-100 text-gray-800',
                        'Unknown': 'bg-gray-100 text-gray-600'
                    };
                    return colors[type] || 'bg-gray-100 text-gray-600';
                },

                openPath(path) {
                    // Copy path to clipboard
                    navigator.clipboard.writeText(path).then(() => {
                        alert('Sökväg kopierad till urklipp: ' + path);
                    }).catch(() => {
                        alert('Sökväg: ' + path);
                    });
                },

                showDetails(project) {
                    this.selectedProject = project;
                    this.showModal = true;
                },

                async loadProjects() {
                    try {
                        const response = await fetch('/api/projects');
                        this.projects = await response.json();
                    } catch (error) {
                        console.error('Error loading projects:', error);
                        alert('Fel vid laddning av projekt');
                    } finally {
                        this.loading = false;
                    }
                },

                init() {
                    this.loadProjects();
                }
            }
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
        projects_file = '/home/micke/project_dashboard/projects.json'
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
        result = subprocess.run(['python3', '/home/micke/project_dashboard/scan_projects.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return jsonify({'success': True, 'message': 'Scan completed successfully'})
        else:
            return jsonify({'success': False, 'error': result.stderr}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Project Dashboard on http://localhost:6888")
    print("📁 Serving projects from: /home/micke/project_dashboard/projects.json")
    app.run(host='0.0.0.0', port=6888, debug=True)