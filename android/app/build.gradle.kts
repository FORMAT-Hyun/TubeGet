import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// 릴리스 서명: android/keystore.properties (git 에 올리지 않음)
//   storeFile=D:/path/tubeget-release.jks
//   storePassword=...
//   keyAlias=tubeget
//   keyPassword=...
val signingProps = Properties().apply {
    val f = rootProject.file("keystore.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}

val ytdlpAndroid = "0.18.1"

android {
    namespace = "io.github.formathyun.tubeget"
    compileSdk = 35

    defaultConfig {
        applicationId = "io.github.formathyun.tubeget"
        minSdk = 24
        targetSdk = 35
        versionCode = 107
        versionName = "0.1.7"
    }

    signingConfigs {
        if (signingProps.getProperty("storeFile") != null) {
            create("release") {
                storeFile = file(signingProps.getProperty("storeFile"))
                storePassword = signingProps.getProperty("storePassword")
                keyAlias = signingProps.getProperty("keyAlias")
                keyPassword = signingProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            // yt-dlp 라이브러리가 리플렉션(jackson)을 써서 코드 줄이기는 끈다
            isMinifyEnabled = false
            signingConfig = signingConfigs.findByName("release") ?: signingConfigs.getByName("debug")
        }
    }

    // CPU 종류마다 따로 만든다 (파이썬·ffmpeg 가 들어 있어서 하나로 합치면 너무 큼)
    splits {
        abi {
            isEnable = true
            reset()
            include("arm64-v8a", "armeabi-v7a", "x86_64")
            isUniversalApk = false
        }
    }

    packaging {
        // 라이브러리의 python/ffmpeg 실행 파일을 꺼내 써야 해서 압축된 채로 두지 않는다
        jniLibs.useLegacyPackaging = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    implementation("io.github.junkfood02.youtubedl-android:library:$ytdlpAndroid")
    implementation("io.github.junkfood02.youtubedl-android:ffmpeg:$ytdlpAndroid")

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-core")
    implementation("io.coil-kt:coil-compose:2.7.0")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303") // 단위 테스트에서 진짜 JSON 파서 사용
}
