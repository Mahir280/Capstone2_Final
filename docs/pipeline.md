# Analysis Workflow

The React + FastAPI app uses a bounded, deterministic workflow for local patent
mapping and decision-support review.

## Steps

1. **Data loading**  
   Records are loaded from CSV/JSON files or the prepared canonical corpus at
   `data/raw/fiber_wearable_patents_sources.csv`. The sample/recovery action
   reloads the same canonical corpus for testing and local-store recovery.

2. **Normalization**  
   Incoming rows are normalized into canonical `PatentRecord` objects with
   stable, source-aware `analysis_id` values.

3. **Local persistence**  
   Normalized records are saved in the local SQLite database used by the app.

4. **Text feature preparation**  
   Important keyword evidence is built from patent title, abstract, and
   keywords.

5. **Technology grouping**  
   Standard grouping places related records into readable technology groups.

6. **Advanced AI optimization**  
   The Genetic Algorithm explores bounded grouping settings and keeps
   configurations based on grouping quality.

7. **Insights**  
   The app generates exploratory overlap signals, deterministic candidate
   application areas, and dataset summary statistics.

8. **Visualization and API/UI presentation**
   Related-patent links and technology groups are assembled into response data
   for the React UI.

## Interpretation Boundary

The workflow supports exploratory patent mapping. It produces reading aids and
analysis quality signals, not legal or commercial decisions, and it does not
provide exhaustive official source coverage.
