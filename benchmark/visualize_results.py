#!/usr/bin/env python3
"""
Visualization Script for Benchmark Results
Creates charts and graphs for the report
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import glob
import os

class BenchmarkVisualizer:
    def __init__(self, results_file=None):
        # Find latest results file if not specified
        if results_file is None:
            results_files = glob.glob("benchmark_results_*.json")
            if not results_files:
                raise FileNotFoundError("No benchmark results found!")
            results_file = sorted(results_files)[-1]
        
        print(f"Loading results from: {results_file}")
        with open(results_file, 'r') as f:
            self.results = json.load(f)
        
        # Create output directory
        self.output_dir = f"visualizations_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def create_response_time_comparison(self):
        """Bar chart comparing response times"""
        models = []
        avg_times = []
        p95_times = []
        
        for model, data in self.results["models"].items():
            metrics = data["metrics"]
            models.append(model.replace(":7b", "").replace(":6.7b", ""))
            avg_times.append(metrics.get("avg_response_time_ms", 0))
            p95_times.append(metrics.get("p95_response_time_ms", 0))
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        x = np.arange(len(models))
        width = 0.35
        
        # Create bars
        bars1 = ax.bar(x - width/2, avg_times, width, label='Average', color='#3498db')
        bars2 = ax.bar(x + width/2, p95_times, width, label='95th Percentile', color='#e74c3c')
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.0f}', ha='center', va='bottom', fontsize=10)
        
        # Customize
        ax.set_xlabel('Model', fontsize=12)
        ax.set_ylabel('Response Time (ms)', fontsize=12)
        ax.set_title('Model Response Time Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(models)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/response_time_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("✅ Created: response_time_comparison.png")
    
    def create_success_rate_chart(self):
        """Create success rate comparison"""
        models = []
        success_rates = []
        colors = ['#2ecc71', '#27ae60', '#f39c12', '#e67e22']
        
        for model, data in self.results["models"].items():
            models.append(model.replace(":7b", "").replace(":6.7b", ""))
            success_rates.append(data["metrics"].get("success_rate", 0) * 100)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        bars = ax.bar(models, success_rates, color=colors)
        
        # Add percentage labels
        for bar, rate in zip(bars, success_rates):
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5,
                   f'{rate:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')
        
        # Customize
        ax.set_ylim(0, 105)
        ax.set_xlabel('Model', fontsize=12)
        ax.set_ylabel('Success Rate (%)', fontsize=12)
        ax.set_title('Query Success Rate by Model', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add reference line at 95%
        ax.axhline(y=95, color='red', linestyle='--', alpha=0.5, label='Target: 95%')
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/success_rate_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("✅ Created: success_rate_comparison.png")
    
    def create_category_performance_heatmap(self):
        """Create heatmap of performance by category"""
        categories = ['direct_search', 'genre_based', 'similarity_search', 
                     'complex_criteria', 'rag_specific', 'edge_cases']
        models = []
        
        # Build data matrix
        data_matrix = []
        
        for model, model_data in self.results["models"].items():
            model_name = model.replace(":7b", "").replace(":6.7b", "")
            models.append(model_name)
            
            row = []
            cat_breakdown = model_data["metrics"].get("category_breakdown", {})
            
            for category in categories:
                if category in cat_breakdown:
                    # Use average response time as metric
                    avg_time = cat_breakdown[category].get("avg_response_time_ms", 0)
                    row.append(avg_time)
                else:
                    row.append(0)
            
            data_matrix.append(row)
        
        # Create heatmap
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Normalize data for color mapping
        data_array = np.array(data_matrix)
        
        im = ax.imshow(data_array, cmap='RdYlGn_r', aspect='auto')
        
        # Set ticks
        ax.set_xticks(np.arange(len(categories)))
        ax.set_yticks(np.arange(len(models)))
        ax.set_xticklabels([cat.replace('_', ' ').title() for cat in categories])
        ax.set_yticklabels(models)
        
        # Rotate the tick labels
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Avg Response Time (ms)', rotation=270, labelpad=20)
        
        # Add text annotations
        for i in range(len(models)):
            for j in range(len(categories)):
                text = ax.text(j, i, f'{data_array[i, j]:.0f}',
                             ha="center", va="center", color="black", fontsize=10)
        
        ax.set_title('Model Performance by Query Category\n(Lower is Better)', 
                    fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/category_performance_heatmap.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("✅ Created: category_performance_heatmap.png")
    
    def create_quality_metrics_radar(self):
        """Create radar chart for quality metrics"""
        # Prepare data
        models = []
        metrics_data = {
            'Success Rate': [],
            'Speed': [],  # Inverse of response time
            'Quality': [],
            'Reliability': []  # Based on P95/Avg ratio
        }
        
        for model, data in self.results["summary"].items():
            models.append(model.replace(":7b", "").replace(":6.7b", ""))
            
            # Normalize metrics to 0-100 scale
            metrics_data['Success Rate'].append(data['success_rate'] * 100)
            
            # Speed: inverse of avg response time, normalized
            max_time = 500  # Assume 500ms as worst acceptable
            speed_score = max(0, (max_time - data['avg_response_time_ms']) / max_time * 100)
            metrics_data['Speed'].append(speed_score)
            
            metrics_data['Quality'].append(data['quality_score'])
            
            # Reliability: how consistent (lower P95/avg ratio is better)
            if data['avg_response_time_ms'] > 0:
                consistency = min(100, (2 - data['p95_response_time_ms'] / data['avg_response_time_ms']) * 100)
            else:
                consistency = 0
            metrics_data['Reliability'].append(max(0, consistency))
        
        # Create radar chart
        categories = list(metrics_data.keys())
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='polar')
        
        # Number of variables
        num_vars = len(categories)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        angles += angles[:1]  # Complete the circle
        
        # Plot each model
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12']
        
        for idx, model in enumerate(models):
            values = [metrics_data[cat][idx] for cat in categories]
            values += values[:1]  # Complete the circle
            
            ax.plot(angles, values, 'o-', linewidth=2, label=model, color=colors[idx])
            ax.fill(angles, values, alpha=0.15, color=colors[idx])
        
        # Fix axis to go in the right order
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        
        # Draw axis lines for each angle and label
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, size=12)
        
        # Set y-axis limits and labels
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], size=10)
        ax.yaxis.grid(True)
        
        # Add legend and title
        plt.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))
        plt.title('Model Performance Overview\n(Higher is Better)', 
                 size=14, fontweight='bold', pad=30)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/quality_metrics_radar.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("✅ Created: quality_metrics_radar.png")
    
    def create_summary_table(self):
        """Create a summary table as image"""
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.axis('tight')
        ax.axis('off')
        
        # Prepare table data
        headers = ['Model', 'Success\nRate (%)', 'Avg Time\n(ms)', 'P95 Time\n(ms)', 
                  'Quality\nScore (%)', 'Best For']
        
        rows = []
        for model, data in self.results["summary"].items():
            model_name = model.replace(":7b", "").replace(":6.7b", "")
            
            # Determine best use case
            if data['avg_response_time_ms'] < 250:
                best_for = "Speed-critical"
            elif data['quality_score'] > 70:
                best_for = "Quality-focused"
            elif data['success_rate'] > 0.98:
                best_for = "Reliability"
            else:
                best_for = "General use"
            
            row = [
                model_name,
                f"{data['success_rate']*100:.1f}",
                f"{data['avg_response_time_ms']:.0f}",
                f"{data['p95_response_time_ms']:.0f}",
                f"{data['quality_score']:.1f}",
                best_for
            ]
            rows.append(row)
        
        # Create table
        table = ax.table(cellText=rows, colLabels=headers, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.2, 1.5)
        
        # Style the table
        for i in range(len(headers)):
            table[(0, i)].set_facecolor('#3498db')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Alternate row colors
        for i in range(1, len(rows) + 1):
            for j in range(len(headers)):
                if i % 2 == 0:
                    table[(i, j)].set_facecolor('#ecf0f1')
                else:
                    table[(i, j)].set_facecolor('white')
        
        plt.title('Model Benchmark Summary Table', fontsize=16, fontweight='bold', pad=20)
        plt.savefig(f"{self.output_dir}/summary_table.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("✅ Created: summary_table.png")
    
    def generate_all_visualizations(self):
        """Generate all visualization types"""
        print(f"\n📊 Generating visualizations in {self.output_dir}/")
        
        try:
            self.create_response_time_comparison()
            self.create_success_rate_chart()
            self.create_category_performance_heatmap()
            self.create_quality_metrics_radar()
            self.create_summary_table()
            
            print(f"\n✅ All visualizations saved to: {self.output_dir}/")
            print("\nGenerated files:")
            for file in os.listdir(self.output_dir):
                print(f"  - {file}")
                
        except Exception as e:
            print(f"❌ Error creating visualizations: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("📈 Benchmark Results Visualizer")
    print("=" * 50)
    
    try:
        visualizer = BenchmarkVisualizer()
        visualizer.generate_all_visualizations()
    except FileNotFoundError:
        print("❌ No benchmark results found!")
        print("Please run benchmark_models.py first.")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
