plugins { id("com.android.application") }

android {
    namespace = "de.listingturbo.mobile"
    compileSdk = 35

    defaultConfig {
        applicationId = "de.listingturbo.mobile"
        minSdk = 26
        targetSdk = 35
        versionCode = 143
        versionName = "1.4.3"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
