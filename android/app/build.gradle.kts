plugins { id("com.android.application") }

android {
    namespace = "de.listingturbo.mobile"
    compileSdk = 35

    defaultConfig {
        applicationId = "de.listingturbo.mobile"
        minSdk = 26
        targetSdk = 35
        versionCode = 144
        versionName = "1.4.4"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
