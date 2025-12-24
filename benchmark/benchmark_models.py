#!/usr/bin/env python3
"""
Model Benchmark Script for AI Book Recommendation System
Tests 4 LLMs: llama3.2, llama2:7b, mistral, deepseek-coder:6.7b
"""

import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Any
import statistics
import sys
import os

class BookRecommendationBenchmark:
    def __init__(self):
        self.ollama_url = "http://ollama:11434"
        self.n8n_webhook = "http://n8n:5678/webhook/invoke_n8n_agent"
        self.book_api = "http://localhost:8000/api/ai"
        
        # Models to test
        self.models = ["llama3.2:latest", "llama2:7b", "mistral:latest", "deepseek-coder:6.7b"]
        
        # Load test queries
        with open('test_queries.json', 'r') as f:
            self.test_data = json.load(f)
            self.test_queries = self.test_data['test_queries']
        
        # Results storage
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "models": {},
            "summary": {}
        }
    
    def test_model_availability(self):
        """Check if all models are available"""
        print("🔍 Checking model availability...")
        
        response = requests.get(f"{self.ollama_url}/api/tags")
        if response.status_code != 200:
            print("❌ Cannot connect to Ollama!")
            return False
        
        available_models = [m['name'] for m in response.json().get('models', [])]
        print(f"Available models: {available_models}")
        
        for model in self.models:
            if model not in available_models:
                print(f"❌ Model {model} not available!")
                return False
        
        print("✅ All models available!")
        return True
    
    def measure_direct_response(self, model: str, prompt: str) -> Dict:
        """Measure direct Ollama response"""
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                },
                timeout=30
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # ms
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "response_time_ms": response_time,
                    "response": data.get("response", ""),
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "eval_count": data.get("eval_count", 0),
                    "total_duration": data.get("total_duration", 0) / 1e6  # to ms
                }
            else:
                return {
                    "success": False,
                    "response_time_ms": response_time,
                    "error": f"Status {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000
            }
    
    def measure_rag_response(self, model: str, query: str) -> Dict:
        """Measure response through n8n RAG pipeline"""
        start_time = time.time()
        
        try:
            # Note: Update this if n8n supports model selection
            response = requests.post(
                self.n8n_webhook,
                json={
                    "sessionId": f"benchmark-{model}-{int(time.time())}",
                    "chatInput": query
                },
                timeout=30
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "rag_response_time_ms": response_time,
                    "rag_response": data
                }
            else:
                return {
                    "success": False,
                    "rag_response_time_ms": response_time,
                    "error": f"Status {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "rag_response_time_ms": (time.time() - start_time) * 1000
            }
    
    def evaluate_response_quality(self, query_data: Dict, response: str) -> Dict:
        """Evaluate response quality based on expected results"""
        quality_scores = {
            "contains_expected_books": 0,
            "hallucination_detected": False,
            "response_length": len(response),
            "mentioned_books": []
        }
        
        # Check for expected books
        if "expected_book_ids" in query_data:
            expected_titles = query_data.get("expected_titles", [])
            for title in expected_titles:
                if title.lower() in response.lower():
                    quality_scores["contains_expected_books"] += 1
                    quality_scores["mentioned_books"].append(title)
        
        # Simple hallucination check (mentions non-existent books)
        fake_indicators = ["Harry Potter and the", "Game of Thrones book"]
        for indicator in fake_indicators:
            if indicator in response:
                quality_scores["hallucination_detected"] = True
        
        return quality_scores
    
    def run_category_benchmark(self, model: str, category: str, queries: List[Dict]) -> Dict:
        """Run benchmark for a specific category"""
        print(f"\n  Testing {category}...")
        category_results = []
        
        for query_data in queries:
            query = query_data["query"]
            print(f"    Query {query_data['id']}: {query[:50]}...")
            
            # Direct model test
            result = self.measure_direct_response(model, query)
            result["query_id"] = query_data["id"]
            result["query"] = query
            result["category"] = category
            result["difficulty"] = query_data.get("difficulty", "medium")
            
            # Evaluate quality if successful
            if result["success"]:
                quality = self.evaluate_response_quality(query_data, result["response"])
                result["quality_scores"] = quality
            
            # RAG test for specific queries
            if "book" in query.lower() or "recommend" in query.lower():
                rag_result = self.measure_rag_response(model, query)
                result.update(rag_result)
            
            category_results.append(result)
            
            # Rate limiting
            time.sleep(1)
        
        return category_results
    
    def calculate_metrics(self, model_results: List[Dict]) -> Dict:
        """Calculate aggregate metrics for a model"""
        successful_results = [r for r in model_results if r["success"]]
        
        if not successful_results:
            return {"error": "No successful results"}
        
        response_times = [r["response_time_ms"] for r in successful_results]
        
        metrics = {
            "total_queries": len(model_results),
            "successful_queries": len(successful_results),
            "success_rate": len(successful_results) / len(model_results),
            "avg_response_time_ms": statistics.mean(response_times),
            "median_response_time_ms": statistics.median(response_times),
            "p95_response_time_ms": sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 1 else response_times[0],
            "min_response_time_ms": min(response_times),
            "max_response_time_ms": max(response_times)
        }
        
        # Category breakdown
        categories = {}
        for result in model_results:
            cat = result["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "successful": 0, "avg_time": []}
            
            categories[cat]["total"] += 1
            if result["success"]:
                categories[cat]["successful"] += 1
                categories[cat]["avg_time"].append(result["response_time_ms"])
        
        # Calculate category averages
        for cat, data in categories.items():
            if data["avg_time"]:
                data["avg_response_time_ms"] = statistics.mean(data["avg_time"])
                data["success_rate"] = data["successful"] / data["total"]
            del data["avg_time"]  # Clean up
        
        metrics["category_breakdown"] = categories
        
        # Quality metrics
        quality_metrics = {
            "avg_response_length": statistics.mean([r.get("quality_scores", {}).get("response_length", 0) for r in successful_results if "quality_scores" in r]),
            "queries_with_expected_books": sum(1 for r in successful_results if r.get("quality_scores", {}).get("contains_expected_books", 0) > 0),
            "hallucination_count": sum(1 for r in successful_results if r.get("quality_scores", {}).get("hallucination_detected", False))
        }
        
        metrics["quality_metrics"] = quality_metrics
        
        return metrics
    
    def run_benchmark(self):
        """Run complete benchmark suite"""
        print("\n🚀 Starting Model Benchmark...")
        print(f"Testing {len(self.models)} models with {sum(len(cat['queries']) for cat in self.test_queries)} queries")
        
        # Check models first
        if not self.test_model_availability():
            print("❌ Model check failed! Exiting...")
            return
        
        # Run benchmarks for each model
        for model in self.models:
            print(f"\n{'='*60}")
            print(f"📊 Benchmarking: {model}")
            print(f"{'='*60}")
            
            model_results = []
            
            # Test each category
            for category_data in self.test_queries:
                category = category_data["category"]
                queries = category_data["queries"]
                
                category_results = self.run_category_benchmark(model, category, queries)
                model_results.extend(category_results)
            
            # Calculate metrics
            metrics = self.calculate_metrics(model_results)
            
            # Store results
            self.results["models"][model] = {
                "metrics": metrics,
                "raw_results": model_results
            }
            
            # Print summary
            print(f"\n📈 {model} Summary:")
            print(f"  Success Rate: {metrics.get('success_rate', 0)*100:.1f}%")
            print(f"  Avg Response Time: {metrics.get('avg_response_time_ms', 0):.2f}ms")
            print(f"  P95 Response Time: {metrics.get('p95_response_time_ms', 0):.2f}ms")
        
        # Generate final summary
        self.generate_summary()
        
        # Save results
        self.save_results()
    
    def generate_summary(self):
        """Generate comparative summary"""
        print("\n" + "="*80)
        print("📊 BENCHMARK SUMMARY")
        print("="*80)
        
        # Header
        headers = ["Model", "Success Rate", "Avg Time (ms)", "P95 Time (ms)", "Quality Score"]
        col_widths = [20, 15, 15, 15, 15]
        
        # Print header
        header_line = ""
        for header, width in zip(headers, col_widths):
            header_line += f"{header:<{width}}"
        print(header_line)
        print("-" * sum(col_widths))
        
        # Summary data
        summary_data = {}
        
        # Print each model
        for model, data in self.results["models"].items():
            metrics = data["metrics"]
            
            quality_score = 0
            if "quality_metrics" in metrics:
                quality_score = (metrics["quality_metrics"]["queries_with_expected_books"] / 
                               metrics["successful_queries"] * 100) if metrics["successful_queries"] > 0 else 0
            
            row = f"{model:<{col_widths[0]}}"
            row += f"{metrics.get('success_rate', 0)*100:<{col_widths[1]}.1f}"
            row += f"{metrics.get('avg_response_time_ms', 0):<{col_widths[2]}.2f}"
            row += f"{metrics.get('p95_response_time_ms', 0):<{col_widths[3]}.2f}"
            row += f"{quality_score:<{col_widths[4]}.1f}"
            
            print(row)
            
            # Store for summary
            summary_data[model] = {
                "success_rate": metrics.get('success_rate', 0),
                "avg_response_time_ms": metrics.get('avg_response_time_ms', 0),
                "p95_response_time_ms": metrics.get('p95_response_time_ms', 0),
                "quality_score": quality_score
            }
        
        self.results["summary"] = summary_data
        
        # Best model analysis
        print("\n🏆 Best Models by Metric:")
        
        # Fastest average
        fastest = min(summary_data.items(), key=lambda x: x[1]["avg_response_time_ms"])
        print(f"  Fastest (avg): {fastest[0]} - {fastest[1]['avg_response_time_ms']:.2f}ms")
        
        # Most reliable
        most_reliable = max(summary_data.items(), key=lambda x: x[1]["success_rate"])
        print(f"  Most Reliable: {most_reliable[0]} - {most_reliable[1]['success_rate']*100:.1f}%")
        
        # Best quality
        best_quality = max(summary_data.items(), key=lambda x: x[1]["quality_score"])
        print(f"  Best Quality: {best_quality[0]} - {best_quality[1]['quality_score']:.1f}%")
    
    def save_results(self):
        """Save detailed results to JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")
        
        # Also create a simplified CSV for easy analysis
        csv_filename = f"benchmark_summary_{timestamp}.csv"
        with open(csv_filename, 'w') as f:
            f.write("Model,Success_Rate,Avg_Response_Time_ms,P95_Response_Time_ms,Quality_Score\n")
            for model, data in self.results["summary"].items():
                f.write(f"{model},{data['success_rate']},{data['avg_response_time_ms']},"
                       f"{data['p95_response_time_ms']},{data['quality_score']}\n")
        
        print(f"📈 Summary CSV saved to: {csv_filename}")

if __name__ == "__main__":
    print("🤖 AI Book Recommendation System - Model Benchmark")
    print("=" * 60)
    
    # Check if test queries file exists
    if not os.path.exists('test_queries.json'):
        print("❌ Error: test_queries.json not found!")
        print("Please create the file with test queries first.")
        sys.exit(1)
    
    # Run benchmark
    benchmark = BookRecommendationBenchmark()
    
    try:
        benchmark.run_benchmark()
        print("\n✅ Benchmark completed successfully!")
    except KeyboardInterrupt:
        print("\n⚠️ Benchmark interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during benchmark: {str(e)}")
        import traceback
        traceback.print_exc()
