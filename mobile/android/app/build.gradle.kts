plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "app.scamtriage"
    compileSdk = 37

    defaultConfig {
        applicationId = "io.github.ag2502.scamtriage"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }

    // Release signing comes from ~/.gradle/gradle.properties (never committed):
    //   scamTriageStoreFile, scamTriageStorePassword, scamTriageKeyAlias, scamTriageKeyPassword
    signingConfigs {
        create("release") {
            val storeFilePath = providers.gradleProperty("scamTriageStoreFile").orNull
            if (storeFilePath != null) {
                storeFile = file(storeFilePath)
                storePassword = providers.gradleProperty("scamTriageStorePassword").get()
                keyAlias = providers.gradleProperty("scamTriageKeyAlias").get()
                keyPassword = providers.gradleProperty("scamTriageKeyPassword").get()
            }
        }
    }
    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            if (providers.gradleProperty("scamTriageStoreFile").isPresent) signingConfig = signingConfigs.getByName("release")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures { compose = true; buildConfig = true }
    // The model files are shared with iOS and the parity tests: mobile/shared/model
    sourceSets.getByName("main").assets.srcDir("../../shared/model")
    androidResources { noCompress += listOf("bin", "txt", "json") }
}

dependencies {
    implementation(project(":engine"))
    implementation("androidx.core:core-ktx:1.19.1")
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.11.0")
    implementation(platform("androidx.compose:compose-bom:2026.09.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
