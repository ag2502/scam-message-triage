# kotlinx.serialization JSON tree API is used reflectively-free; keep the engine API surface.
-keep class app.scamtriage.engine.** { *; }
-dontwarn kotlinx.serialization.**
