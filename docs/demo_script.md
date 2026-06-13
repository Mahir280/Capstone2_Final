# Presentation Walkthrough

Use this path for a short, stable presentation of the implemented React +
FastAPI application.

1. Start the primary app with `start_app.bat` and open
   `http://127.0.0.1:8000`.
2. Open **Data Sources** and load the prepared curated dataset. Explain that
   the sample/recovery action reloads the same canonical corpus, not a separate
   demo CSV.
3. Open **Dataset Insights** and review corpus coverage, authority,
   organization, year, and keyword summaries.
4. Open **Patent Search** and search for a term such as `conductive yarn`,
   `textile electrode`, or `health monitoring`.
5. Open a result in **Patent Profile** and explain the source authority, key
   facts, important technical keywords, candidate application areas,
   relationship strength, and related patents.
6. Emphasize that related-patent links and overlap signals are reading aids, not
   legal conclusions.
7. Open **Patent Landscape** and show the focused view for the selected patent,
   then switch to the full landscape if time allows.
8. Explain that technology groups are formed from saved patent titles,
   abstracts, and keywords.
9. Open **Advanced AI** only if the presentation needs the biomimetic
   optimization section; compare standard grouping with Genetic Algorithm
   optimized grouping quality.
10. Close with the main limitations: curated dataset scope, no live
    patent-office API integration, lexical text methods, small-dataset
    sensitivity, and non-legal/non-commercial interpretation.
