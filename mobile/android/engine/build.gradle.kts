// Pure-Kotlin port of scam_triage (signals + model + triage). No Android dependencies,
// so parity tests run on the JVM and the same code ships inside the app.
plugins {
    id("org.jetbrains.kotlin.jvm")
}

// Compile with the installed JDK (21) but emit Java 17 bytecode for Android compatibility.
java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}
kotlin {
    compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) }
}

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.11.0")
    testImplementation(kotlin("test"))
    testImplementation("org.junit.jupiter:junit-jupiter:5.13.4")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.test {
    useJUnitPlatform()
    systemProperty("sharedDir", rootDir.resolve("../shared").absolutePath)
    testLogging { events("failed"); showStandardStreams = true; exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL }
}
