// ListingTurbo Native Backend v1.1
// C++17, header-only OpenCL loader, deterministic CPU reference path.
#define NOMINMAX

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <string>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#else
#include <dlfcn.h>
#endif

namespace lt {

constexpr std::uint32_t ABI_VERSION = 1;
constexpr std::uint32_t BACKEND_CPU = 1u;
constexpr std::uint32_t BACKEND_OPENCL = 2u;
constexpr int OK = 0;
constexpr int ERR_ARGUMENT = 1;
constexpr int ERR_RUNTIME = 2;

using cl_int = std::int32_t;
using cl_uint = std::uint32_t;
using cl_ulong = std::uint64_t;
using cl_bool = cl_uint;
using cl_bitfield = cl_ulong;
using cl_device_type = cl_bitfield;
using cl_context_properties = intptr_t;
using cl_command_queue_properties = cl_bitfield;

struct _cl_platform_id;
struct _cl_device_id;
struct _cl_context;
struct _cl_command_queue;
struct _cl_mem;
struct _cl_program;
struct _cl_kernel;

using cl_platform_id = _cl_platform_id*;
using cl_device_id = _cl_device_id*;
using cl_context = _cl_context*;
using cl_command_queue = _cl_command_queue*;
using cl_mem = _cl_mem*;
using cl_program = _cl_program*;
using cl_kernel = _cl_kernel*;
using cl_event = void*;

constexpr cl_int CL_SUCCESS = 0;
constexpr cl_device_type CL_DEVICE_TYPE_CPU = 1ull << 1;
constexpr cl_device_type CL_DEVICE_TYPE_GPU = 1ull << 2;
constexpr cl_bitfield CL_MEM_READ_ONLY = 1ull << 2;
constexpr cl_bitfield CL_MEM_WRITE_ONLY = 1ull << 1;
constexpr cl_bool CL_TRUE = 1;
constexpr cl_uint CL_PROGRAM_BUILD_LOG = 0x1183;

struct PublicMetrics {
    std::uint32_t abi_version;
    std::uint32_t backend_flags;
    double brightness;
    double contrast;
    double sharpness;
    std::uint64_t pixels;
    std::uint32_t status;
    char message[256];
};

struct CpuStats {
    double brightness = 0.0;
    double contrast = 0.0;
    double sharpness = 0.0;
    std::uint64_t pixels = 0;
};

struct PartialStats {
    float sum;
    float sumsq;
    float edge;
    float count;
};

static float luma_at(const std::uint8_t* src, int x, int y, int width, int height, int stride) noexcept {
    x = std::clamp(x, 0, width - 1);
    y = std::clamp(y, 0, height - 1);
    const std::uint8_t* pixel = src + static_cast<std::size_t>(y) * static_cast<std::size_t>(stride) + static_cast<std::size_t>(x) * 3u;
    return 0.299f * static_cast<float>(pixel[0]) + 0.587f * static_cast<float>(pixel[1]) + 0.114f * static_cast<float>(pixel[2]);
}

static CpuStats analyze_cpu(const std::uint8_t* src, int width, int height, int stride) noexcept {
    CpuStats stats{};
    if (src == nullptr || width <= 0 || height <= 0 || stride < width * 3) {
        return stats;
    }

    const std::uint64_t pixels = static_cast<std::uint64_t>(width) * static_cast<std::uint64_t>(height);
    double sum = 0.0;
    double sumsq = 0.0;
    double edge = 0.0;

    for (int y = 0; y < height; ++y) {
        const std::uint8_t* row = src + static_cast<std::size_t>(y) * static_cast<std::size_t>(stride);
        for (int x = 0; x < width; ++x) {
            const std::uint8_t* pixel = row + static_cast<std::size_t>(x) * 3u;
            const double luma = 0.299 * static_cast<double>(pixel[0]) + 0.587 * static_cast<double>(pixel[1]) + 0.114 * static_cast<double>(pixel[2]);
            sum += luma;
            sumsq += luma * luma;
        }
    }

    if (width > 2 && height > 2) {
        for (int y = 1; y < height - 1; ++y) {
            for (int x = 1; x < width - 1; ++x) {
                const double center = luma_at(src, x, y, width, height, stride);
                const double left = luma_at(src, x - 1, y, width, height, stride);
                const double right = luma_at(src, x + 1, y, width, height, stride);
                const double up = luma_at(src, x, y - 1, width, height, stride);
                const double down = luma_at(src, x, y + 1, width, height, stride);
                edge += std::abs(4.0 * center - left - right - up - down);
            }
        }
    }

    const double mean = pixels > 0 ? sum / static_cast<double>(pixels) : 0.0;
    const double variance = pixels > 0 ? std::max(0.0, sumsq / static_cast<double>(pixels) - mean * mean) : 0.0;
    stats.brightness = mean;
    stats.contrast = std::sqrt(variance);
    stats.sharpness = pixels > 0 ? edge / static_cast<double>(pixels) : 0.0;
    stats.pixels = pixels;
    return stats;
}

static std::uint8_t clamp_u8(float value) noexcept {
    if (value <= 0.0f) {
        return 0;
    }
    if (value >= 255.0f) {
        return 255;
    }
    return static_cast<std::uint8_t>(value + 0.5f);
}

static int enhance_cpu(
    const std::uint8_t* src,
    int width,
    int height,
    int src_stride,
    std::uint8_t* dst,
    int dst_stride,
    float brightness_factor,
    float contrast_factor,
    float sharpen_amount
) noexcept {
    if (src == nullptr || dst == nullptr || width <= 0 || height <= 0 || src_stride < width * 3 || dst_stride < width * 3) {
        return ERR_ARGUMENT;
    }

    brightness_factor = std::clamp(brightness_factor, 0.25f, 3.0f);
    contrast_factor = std::clamp(contrast_factor, 0.25f, 3.0f);
    sharpen_amount = std::clamp(sharpen_amount, 0.0f, 2.0f);

    std::vector<std::uint8_t> adjusted(static_cast<std::size_t>(width) * static_cast<std::size_t>(height) * 3u);
    auto pixel_at = [&](int x, int y, int c) -> std::uint8_t {
        x = std::clamp(x, 0, width - 1);
        y = std::clamp(y, 0, height - 1);
        return adjusted[(static_cast<std::size_t>(y) * static_cast<std::size_t>(width) + static_cast<std::size_t>(x)) * 3u + static_cast<std::size_t>(c)];
    };

    for (int y = 0; y < height; ++y) {
        const std::uint8_t* in_row = src + static_cast<std::size_t>(y) * static_cast<std::size_t>(src_stride);
        for (int x = 0; x < width; ++x) {
            const std::uint8_t* in_pixel = in_row + static_cast<std::size_t>(x) * 3u;
            std::uint8_t* out_pixel = adjusted.data() + (static_cast<std::size_t>(y) * static_cast<std::size_t>(width) + static_cast<std::size_t>(x)) * 3u;
            for (int c = 0; c < 3; ++c) {
                const float centered = (static_cast<float>(in_pixel[c]) - 128.0f) * contrast_factor + 128.0f;
                out_pixel[c] = clamp_u8(centered * brightness_factor);
            }
        }
    }

    for (int y = 0; y < height; ++y) {
        std::uint8_t* out_row = dst + static_cast<std::size_t>(y) * static_cast<std::size_t>(dst_stride);
        for (int x = 0; x < width; ++x) {
            std::uint8_t* out_pixel = out_row + static_cast<std::size_t>(x) * 3u;
            for (int c = 0; c < 3; ++c) {
                if (sharpen_amount <= 0.001f || x == 0 || y == 0 || x == width - 1 || y == height - 1) {
                    out_pixel[c] = pixel_at(x, y, c);
                    continue;
                }
                const float center = static_cast<float>(pixel_at(x, y, c));
                const float lap = 4.0f * center
                    - static_cast<float>(pixel_at(x - 1, y, c))
                    - static_cast<float>(pixel_at(x + 1, y, c))
                    - static_cast<float>(pixel_at(x, y - 1, c))
                    - static_cast<float>(pixel_at(x, y + 1, c));
                out_pixel[c] = clamp_u8(center + sharpen_amount * lap);
            }
        }
    }

    return OK;
}

#ifdef _WIN32
using LibHandle = HMODULE;
static LibHandle open_library(const char* name) noexcept { return LoadLibraryA(name); }
static void* load_symbol(LibHandle library, const char* name) noexcept { return reinterpret_cast<void*>(GetProcAddress(library, name)); }
static void close_library(LibHandle library) noexcept { if (library != nullptr) { FreeLibrary(library); } }
#else
using LibHandle = void*;
static LibHandle open_library(const char* name) noexcept { return dlopen(name, RTLD_LAZY | RTLD_LOCAL); }
static void* load_symbol(LibHandle library, const char* name) noexcept { return dlsym(library, name); }
static void close_library(LibHandle library) noexcept { if (library != nullptr) { dlclose(library); } }
#endif

struct OpenClApi {
    using clGetPlatformIDs_t = cl_int (*)(cl_uint, cl_platform_id*, cl_uint*);
    using clGetDeviceIDs_t = cl_int (*)(cl_platform_id, cl_device_type, cl_uint, cl_device_id*, cl_uint*);
    using clCreateContext_t = cl_context (*)(const cl_context_properties*, cl_uint, const cl_device_id*, void (*)(const char*, const void*, std::size_t, void*), void*, cl_int*);
    using clCreateCommandQueue_t = cl_command_queue (*)(cl_context, cl_device_id, cl_command_queue_properties, cl_int*);
    using clCreateProgramWithSource_t = cl_program (*)(cl_context, cl_uint, const char**, const std::size_t*, cl_int*);
    using clBuildProgram_t = cl_int (*)(cl_program, cl_uint, const cl_device_id*, const char*, void (*)(cl_program, void*), void*);
    using clGetProgramBuildInfo_t = cl_int (*)(cl_program, cl_device_id, cl_uint, std::size_t, void*, std::size_t*);
    using clCreateKernel_t = cl_kernel (*)(cl_program, const char*, cl_int*);
    using clCreateBuffer_t = cl_mem (*)(cl_context, cl_bitfield, std::size_t, void*, cl_int*);
    using clEnqueueWriteBuffer_t = cl_int (*)(cl_command_queue, cl_mem, cl_bool, std::size_t, std::size_t, const void*, cl_uint, const cl_event*, cl_event*);
    using clEnqueueReadBuffer_t = cl_int (*)(cl_command_queue, cl_mem, cl_bool, std::size_t, std::size_t, void*, cl_uint, const cl_event*, cl_event*);
    using clSetKernelArg_t = cl_int (*)(cl_kernel, cl_uint, std::size_t, const void*);
    using clEnqueueNDRangeKernel_t = cl_int (*)(cl_command_queue, cl_kernel, cl_uint, const std::size_t*, const std::size_t*, const std::size_t*, cl_uint, const cl_event*, cl_event*);
    using clFinish_t = cl_int (*)(cl_command_queue);
    using clReleaseMemObject_t = cl_int (*)(cl_mem);
    using clReleaseKernel_t = cl_int (*)(cl_kernel);
    using clReleaseProgram_t = cl_int (*)(cl_program);
    using clReleaseCommandQueue_t = cl_int (*)(cl_command_queue);
    using clReleaseContext_t = cl_int (*)(cl_context);

    LibHandle library = nullptr;
    clGetPlatformIDs_t clGetPlatformIDs = nullptr;
    clGetDeviceIDs_t clGetDeviceIDs = nullptr;
    clCreateContext_t clCreateContext = nullptr;
    clCreateCommandQueue_t clCreateCommandQueue = nullptr;
    clCreateProgramWithSource_t clCreateProgramWithSource = nullptr;
    clBuildProgram_t clBuildProgram = nullptr;
    clGetProgramBuildInfo_t clGetProgramBuildInfo = nullptr;
    clCreateKernel_t clCreateKernel = nullptr;
    clCreateBuffer_t clCreateBuffer = nullptr;
    clEnqueueWriteBuffer_t clEnqueueWriteBuffer = nullptr;
    clEnqueueReadBuffer_t clEnqueueReadBuffer = nullptr;
    clSetKernelArg_t clSetKernelArg = nullptr;
    clEnqueueNDRangeKernel_t clEnqueueNDRangeKernel = nullptr;
    clFinish_t clFinish = nullptr;
    clReleaseMemObject_t clReleaseMemObject = nullptr;
    clReleaseKernel_t clReleaseKernel = nullptr;
    clReleaseProgram_t clReleaseProgram = nullptr;
    clReleaseCommandQueue_t clReleaseCommandQueue = nullptr;
    clReleaseContext_t clReleaseContext = nullptr;

    bool loaded = false;
    std::string message = "OpenCL nicht geladen";

    bool load() {
        if (loaded) {
            return true;
        }
#ifdef _WIN32
        library = open_library("OpenCL.dll");
#else
        library = open_library("libOpenCL.so.1");
        if (library == nullptr) {
            library = open_library("libOpenCL.so");
        }
#endif
        if (library == nullptr) {
            message = "OpenCL Runtime nicht gefunden";
            return false;
        }

#define LT_LOAD_CL(name) do { \
    name = reinterpret_cast<name##_t>(load_symbol(library, #name)); \
    if (name == nullptr) { message = std::string("OpenCL Symbol fehlt: ") + #name; close_library(library); library = nullptr; return false; } \
} while (0)
        LT_LOAD_CL(clGetPlatformIDs);
        LT_LOAD_CL(clGetDeviceIDs);
        LT_LOAD_CL(clCreateContext);
        LT_LOAD_CL(clCreateCommandQueue);
        LT_LOAD_CL(clCreateProgramWithSource);
        LT_LOAD_CL(clBuildProgram);
        LT_LOAD_CL(clGetProgramBuildInfo);
        LT_LOAD_CL(clCreateKernel);
        LT_LOAD_CL(clCreateBuffer);
        LT_LOAD_CL(clEnqueueWriteBuffer);
        LT_LOAD_CL(clEnqueueReadBuffer);
        LT_LOAD_CL(clSetKernelArg);
        LT_LOAD_CL(clEnqueueNDRangeKernel);
        LT_LOAD_CL(clFinish);
        LT_LOAD_CL(clReleaseMemObject);
        LT_LOAD_CL(clReleaseKernel);
        LT_LOAD_CL(clReleaseProgram);
        LT_LOAD_CL(clReleaseCommandQueue);
        LT_LOAD_CL(clReleaseContext);
#undef LT_LOAD_CL
        loaded = true;
        message = "OpenCL Runtime geladen";
        return true;
    }
};

static constexpr const char* KERNEL_SOURCE = R"CLC(
__kernel void lt_stats_rgb8(
    __global const uchar* src,
    const int width,
    const int height,
    const int stride,
    __global float4* partial
) {
    const int gid = get_global_id(0);
    const int lid = get_local_id(0);
    const int group = get_group_id(0);
    const int local_size = get_local_size(0);
    __local float l_sum[256];
    __local float l_sumsq[256];
    __local float l_edge[256];
    __local float l_count[256];

    const int pixels = width * height;
    float sum = 0.0f;
    float sumsq = 0.0f;
    float edge = 0.0f;
    float count = 0.0f;

    if (gid < pixels) {
        const int y = gid / width;
        const int x = gid - y * width;
        const int p = y * stride + x * 3;
        const float c = 0.299f * src[p] + 0.587f * src[p + 1] + 0.114f * src[p + 2];
        sum = c;
        sumsq = c * c;
        count = 1.0f;
        if (x > 0 && y > 0 && x < width - 1 && y < height - 1) {
            const int lp = y * stride + (x - 1) * 3;
            const int rp = y * stride + (x + 1) * 3;
            const int up = (y - 1) * stride + x * 3;
            const int dp = (y + 1) * stride + x * 3;
            const float left = 0.299f * src[lp] + 0.587f * src[lp + 1] + 0.114f * src[lp + 2];
            const float right = 0.299f * src[rp] + 0.587f * src[rp + 1] + 0.114f * src[rp + 2];
            const float upv = 0.299f * src[up] + 0.587f * src[up + 1] + 0.114f * src[up + 2];
            const float down = 0.299f * src[dp] + 0.587f * src[dp + 1] + 0.114f * src[dp + 2];
            edge = fabs(4.0f * c - left - right - upv - down);
        }
    }

    l_sum[lid] = sum;
    l_sumsq[lid] = sumsq;
    l_edge[lid] = edge;
    l_count[lid] = count;
    barrier(CLK_LOCAL_MEM_FENCE);

    for (int offset = local_size >> 1; offset > 0; offset >>= 1) {
        if (lid < offset) {
            l_sum[lid] += l_sum[lid + offset];
            l_sumsq[lid] += l_sumsq[lid + offset];
            l_edge[lid] += l_edge[lid + offset];
            l_count[lid] += l_count[lid + offset];
        }
        barrier(CLK_LOCAL_MEM_FENCE);
    }

    if (lid == 0) {
        partial[group] = (float4)(l_sum[0], l_sumsq[0], l_edge[0], l_count[0]);
    }
}

__kernel void lt_enhance_rgb8(
    __global const uchar* src,
    const int width,
    const int height,
    const int src_stride,
    __global uchar* dst,
    const int dst_stride,
    const float brightness,
    const float contrast
) {
    const int gid = get_global_id(0);
    const int pixels = width * height;
    if (gid >= pixels) {
        return;
    }
    const int y = gid / width;
    const int x = gid - y * width;
    const int ip = y * src_stride + x * 3;
    const int op = y * dst_stride + x * 3;
    for (int c = 0; c < 3; ++c) {
        float v = (((float)src[ip + c] - 128.0f) * contrast + 128.0f) * brightness;
        v = clamp(v, 0.0f, 255.0f);
        dst[op + c] = (uchar)(v + 0.5f);
    }
}
)CLC";

struct NativeRuntime {
    std::mutex mutex;
    bool attempted = false;
    bool ready = false;
    std::string message = "OpenCL nicht initialisiert";
    OpenClApi api{};
    cl_device_id device = nullptr;
    cl_context context = nullptr;
    cl_command_queue queue = nullptr;
    cl_program program = nullptr;
    cl_kernel stats_kernel = nullptr;
    cl_kernel enhance_kernel = nullptr;

    ~NativeRuntime() {
        release();
    }

    void release() noexcept {
        if (api.loaded) {
            if (stats_kernel != nullptr) { api.clReleaseKernel(stats_kernel); stats_kernel = nullptr; }
            if (enhance_kernel != nullptr) { api.clReleaseKernel(enhance_kernel); enhance_kernel = nullptr; }
            if (program != nullptr) { api.clReleaseProgram(program); program = nullptr; }
            if (queue != nullptr) { api.clReleaseCommandQueue(queue); queue = nullptr; }
            if (context != nullptr) { api.clReleaseContext(context); context = nullptr; }
        }
        if (api.library != nullptr) {
            close_library(api.library);
            api.library = nullptr;
        }
        api.loaded = false;
        ready = false;
    }

    bool ensure() {
        std::lock_guard<std::mutex> guard(mutex);
        if (attempted) {
            return ready;
        }
        attempted = true;
        if (!api.load()) {
            message = api.message;
            return false;
        }

        cl_uint platform_count = 0;
        cl_int err = api.clGetPlatformIDs(0, nullptr, &platform_count);
        if (err != CL_SUCCESS || platform_count == 0) {
            message = "OpenCL: keine Plattform gefunden";
            return false;
        }
        std::vector<cl_platform_id> platforms(platform_count);
        err = api.clGetPlatformIDs(platform_count, platforms.data(), nullptr);
        if (err != CL_SUCCESS) {
            message = "OpenCL: Plattformliste konnte nicht gelesen werden";
            return false;
        }

        for (cl_platform_id platform : platforms) {
            if (pick_device(platform, CL_DEVICE_TYPE_GPU) || pick_device(platform, CL_DEVICE_TYPE_CPU)) {
                break;
            }
        }
        if (device == nullptr) {
            message = "OpenCL: kein GPU/CPU-Gerät verfügbar";
            return false;
        }

        context = api.clCreateContext(nullptr, 1, &device, nullptr, nullptr, &err);
        if (err != CL_SUCCESS || context == nullptr) {
            message = "OpenCL: Kontext konnte nicht erstellt werden";
            return false;
        }
        queue = api.clCreateCommandQueue(context, device, 0, &err);
        if (err != CL_SUCCESS || queue == nullptr) {
            message = "OpenCL: Command Queue konnte nicht erstellt werden";
            return false;
        }

        const char* source = KERNEL_SOURCE;
        const std::size_t source_len = std::strlen(KERNEL_SOURCE);
        program = api.clCreateProgramWithSource(context, 1, &source, &source_len, &err);
        if (err != CL_SUCCESS || program == nullptr) {
            message = "OpenCL: Programmerstellung fehlgeschlagen";
            return false;
        }
        err = api.clBuildProgram(program, 1, &device, "", nullptr, nullptr);
        if (err != CL_SUCCESS) {
            message = std::string("OpenCL Buildfehler: ") + build_log();
            return false;
        }
        stats_kernel = api.clCreateKernel(program, "lt_stats_rgb8", &err);
        if (err != CL_SUCCESS || stats_kernel == nullptr) {
            message = "OpenCL: Stats-Kernel konnte nicht erstellt werden";
            return false;
        }
        enhance_kernel = api.clCreateKernel(program, "lt_enhance_rgb8", &err);
        if (err != CL_SUCCESS || enhance_kernel == nullptr) {
            message = "OpenCL: Enhance-Kernel konnte nicht erstellt werden";
            return false;
        }
        ready = true;
        message = "OpenCL aktiv; CPU-Referenz bleibt Fallback";
        return true;
    }

    bool pick_device(cl_platform_id platform, cl_device_type type) {
        cl_uint count = 0;
        cl_int err = api.clGetDeviceIDs(platform, type, 0, nullptr, &count);
        if (err != CL_SUCCESS || count == 0) {
            return false;
        }
        std::vector<cl_device_id> devices(count);
        err = api.clGetDeviceIDs(platform, type, count, devices.data(), nullptr);
        if (err != CL_SUCCESS || devices.empty()) {
            return false;
        }
        device = devices.front();
        return true;
    }

    std::string build_log() {
        if (program == nullptr || device == nullptr || api.clGetProgramBuildInfo == nullptr) {
            return "kein Buildlog";
        }
        std::size_t size = 0;
        api.clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, 0, nullptr, &size);
        if (size == 0) {
            return "leerer Buildlog";
        }
        std::vector<char> buffer(size + 1, '\0');
        api.clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, size, buffer.data(), nullptr);
        return std::string(buffer.data());
    }

    bool analyze_opencl(const std::uint8_t* src, int width, int height, int stride, CpuStats& out) {
        if (!ensure()) {
            return false;
        }
        std::lock_guard<std::mutex> guard(mutex);
        const std::uint64_t pixels64 = static_cast<std::uint64_t>(width) * static_cast<std::uint64_t>(height);
        if (pixels64 == 0 || pixels64 > static_cast<std::uint64_t>(1u << 31)) {
            return false;
        }
        const std::size_t src_size = static_cast<std::size_t>(stride) * static_cast<std::size_t>(height);
        constexpr std::size_t local = 256;
        const std::size_t groups = (static_cast<std::size_t>(pixels64) + local - 1u) / local;
        const std::size_t global = groups * local;
        const std::size_t partial_size = groups * sizeof(PartialStats);
        cl_int err = CL_SUCCESS;
        cl_mem src_buffer = api.clCreateBuffer(context, CL_MEM_READ_ONLY, src_size, nullptr, &err);
        if (err != CL_SUCCESS || src_buffer == nullptr) {
            return false;
        }
        cl_mem partial_buffer = api.clCreateBuffer(context, CL_MEM_WRITE_ONLY, partial_size, nullptr, &err);
        if (err != CL_SUCCESS || partial_buffer == nullptr) {
            api.clReleaseMemObject(src_buffer);
            return false;
        }
        err = api.clEnqueueWriteBuffer(queue, src_buffer, CL_TRUE, 0, src_size, src, 0, nullptr, nullptr);
        if (err != CL_SUCCESS) {
            api.clReleaseMemObject(partial_buffer);
            api.clReleaseMemObject(src_buffer);
            return false;
        }
        err  = api.clSetKernelArg(stats_kernel, 0, sizeof(cl_mem), &src_buffer);
        err |= api.clSetKernelArg(stats_kernel, 1, sizeof(int), &width);
        err |= api.clSetKernelArg(stats_kernel, 2, sizeof(int), &height);
        err |= api.clSetKernelArg(stats_kernel, 3, sizeof(int), &stride);
        err |= api.clSetKernelArg(stats_kernel, 4, sizeof(cl_mem), &partial_buffer);
        if (err != CL_SUCCESS) {
            api.clReleaseMemObject(partial_buffer);
            api.clReleaseMemObject(src_buffer);
            return false;
        }
        err = api.clEnqueueNDRangeKernel(queue, stats_kernel, 1, nullptr, &global, &local, 0, nullptr, nullptr);
        if (err != CL_SUCCESS) {
            api.clReleaseMemObject(partial_buffer);
            api.clReleaseMemObject(src_buffer);
            return false;
        }
        std::vector<PartialStats> partial(groups);
        err = api.clEnqueueReadBuffer(queue, partial_buffer, CL_TRUE, 0, partial_size, partial.data(), 0, nullptr, nullptr);
        api.clFinish(queue);
        api.clReleaseMemObject(partial_buffer);
        api.clReleaseMemObject(src_buffer);
        if (err != CL_SUCCESS) {
            return false;
        }
        double sum = 0.0;
        double sumsq = 0.0;
        double edge = 0.0;
        double count = 0.0;
        for (const PartialStats& item : partial) {
            sum += item.sum;
            sumsq += item.sumsq;
            edge += item.edge;
            count += item.count;
        }
        if (count <= 0.0) {
            return false;
        }
        const double mean = sum / count;
        out.brightness = mean;
        out.contrast = std::sqrt(std::max(0.0, sumsq / count - mean * mean));
        out.sharpness = edge / count;
        out.pixels = static_cast<std::uint64_t>(count);
        return true;
    }

    bool enhance_opencl(
        const std::uint8_t* src,
        int width,
        int height,
        int src_stride,
        std::uint8_t* dst,
        int dst_stride,
        float brightness_factor,
        float contrast_factor
    ) {
        if (!ensure()) {
            return false;
        }
        std::lock_guard<std::mutex> guard(mutex);
        const std::uint64_t pixels64 = static_cast<std::uint64_t>(width) * static_cast<std::uint64_t>(height);
        const std::size_t src_size = static_cast<std::size_t>(src_stride) * static_cast<std::size_t>(height);
        const std::size_t dst_size = static_cast<std::size_t>(dst_stride) * static_cast<std::size_t>(height);
        constexpr std::size_t local = 256;
        const std::size_t global = ((static_cast<std::size_t>(pixels64) + local - 1u) / local) * local;
        cl_int err = CL_SUCCESS;
        cl_mem src_buffer = api.clCreateBuffer(context, CL_MEM_READ_ONLY, src_size, nullptr, &err);
        if (err != CL_SUCCESS || src_buffer == nullptr) {
            return false;
        }
        cl_mem dst_buffer = api.clCreateBuffer(context, CL_MEM_WRITE_ONLY, dst_size, nullptr, &err);
        if (err != CL_SUCCESS || dst_buffer == nullptr) {
            api.clReleaseMemObject(src_buffer);
            return false;
        }
        err = api.clEnqueueWriteBuffer(queue, src_buffer, CL_TRUE, 0, src_size, src, 0, nullptr, nullptr);
        if (err != CL_SUCCESS) {
            api.clReleaseMemObject(dst_buffer);
            api.clReleaseMemObject(src_buffer);
            return false;
        }
        err  = api.clSetKernelArg(enhance_kernel, 0, sizeof(cl_mem), &src_buffer);
        err |= api.clSetKernelArg(enhance_kernel, 1, sizeof(int), &width);
        err |= api.clSetKernelArg(enhance_kernel, 2, sizeof(int), &height);
        err |= api.clSetKernelArg(enhance_kernel, 3, sizeof(int), &src_stride);
        err |= api.clSetKernelArg(enhance_kernel, 4, sizeof(cl_mem), &dst_buffer);
        err |= api.clSetKernelArg(enhance_kernel, 5, sizeof(int), &dst_stride);
        err |= api.clSetKernelArg(enhance_kernel, 6, sizeof(float), &brightness_factor);
        err |= api.clSetKernelArg(enhance_kernel, 7, sizeof(float), &contrast_factor);
        if (err != CL_SUCCESS) {
            api.clReleaseMemObject(dst_buffer);
            api.clReleaseMemObject(src_buffer);
            return false;
        }
        err = api.clEnqueueNDRangeKernel(queue, enhance_kernel, 1, nullptr, &global, &local, 0, nullptr, nullptr);
        if (err != CL_SUCCESS) {
            api.clReleaseMemObject(dst_buffer);
            api.clReleaseMemObject(src_buffer);
            return false;
        }
        err = api.clEnqueueReadBuffer(queue, dst_buffer, CL_TRUE, 0, dst_size, dst, 0, nullptr, nullptr);
        api.clFinish(queue);
        api.clReleaseMemObject(dst_buffer);
        api.clReleaseMemObject(src_buffer);
        return err == CL_SUCCESS;
    }
};

static NativeRuntime& runtime() {
    static NativeRuntime instance;
    return instance;
}

static void write_message(char* target, std::size_t target_size, const std::string& message) noexcept {
    if (target == nullptr || target_size == 0) {
        return;
    }
#ifdef _WIN32
    strncpy_s(target, target_size, message.c_str(), _TRUNCATE);
#else
    std::snprintf(target, target_size, "%s", message.c_str());
#endif
}

static void write_public_message(PublicMetrics* out, const std::string& message) noexcept {
    if (out == nullptr) {
        return;
    }
    write_message(out->message, sizeof(out->message), message);
}

} // namespace lt

extern "C" {

#if defined(_WIN32)
#define LT_API __declspec(dllexport)
#else
#define LT_API __attribute__((visibility("default")))
#endif

LT_API const char* lt_native_version() noexcept {
    return "ListingTurbo Native Backend 1.1.0 / ABI 1 / C++17 / OpenCL dynamic";
}

LT_API int lt_backend_info(char* buffer, int buffer_size) noexcept {
    if (buffer == nullptr || buffer_size <= 0) {
        return lt::ERR_ARGUMENT;
    }
    lt::NativeRuntime& rt = lt::runtime();
    const bool opencl = rt.ensure();
    const std::string info = std::string("version=") + lt_native_version()
        + "; cpu=aktiv"
        + "; opencl=" + (opencl ? "aktiv" : "inaktiv")
        + "; detail=" + rt.message;
    lt::write_message(buffer, static_cast<std::size_t>(buffer_size), info);
    return lt::OK;
}

LT_API int lt_analyze_rgb8(
    const std::uint8_t* src,
    int width,
    int height,
    int stride,
    lt::PublicMetrics* out
) noexcept {
    if (out == nullptr) {
        return lt::ERR_ARGUMENT;
    }
    std::memset(out, 0, sizeof(*out));
    out->abi_version = lt::ABI_VERSION;
    out->backend_flags = lt::BACKEND_CPU;
    if (src == nullptr || width <= 0 || height <= 0 || stride < width * 3) {
        out->status = lt::ERR_ARGUMENT;
        lt::write_public_message(out, "Ungültige RGB8-Eingabe");
        return lt::ERR_ARGUMENT;
    }

    lt::CpuStats stats{};
    lt::NativeRuntime& rt = lt::runtime();
    if (rt.analyze_opencl(src, width, height, stride, stats)) {
        out->backend_flags = lt::BACKEND_CPU | lt::BACKEND_OPENCL;
        lt::write_public_message(out, "Analyse über OpenCL-Kernel; CPU-Fallback verfügbar");
    } else {
        stats = lt::analyze_cpu(src, width, height, stride);
        lt::write_public_message(out, "Analyse über deterministische C++-CPU-Referenz");
    }
    out->brightness = stats.brightness;
    out->contrast = stats.contrast;
    out->sharpness = stats.sharpness;
    out->pixels = stats.pixels;
    out->status = lt::OK;
    return lt::OK;
}

LT_API int lt_enhance_rgb8(
    const std::uint8_t* src,
    int width,
    int height,
    int src_stride,
    std::uint8_t* dst,
    int dst_stride,
    float brightness_factor,
    float contrast_factor,
    float sharpen_amount,
    lt::PublicMetrics* out
) noexcept {
    if (out != nullptr) {
        std::memset(out, 0, sizeof(*out));
        out->abi_version = lt::ABI_VERSION;
        out->backend_flags = lt::BACKEND_CPU;
    }
    if (src == nullptr || dst == nullptr || width <= 0 || height <= 0 || src_stride < width * 3 || dst_stride < width * 3) {
        if (out != nullptr) {
            out->status = lt::ERR_ARGUMENT;
            lt::write_public_message(out, "Ungültige RGB8-Eingabe");
        }
        return lt::ERR_ARGUMENT;
    }

    int result = lt::ERR_RUNTIME;
    lt::NativeRuntime& rt = lt::runtime();
    if (sharpen_amount <= 0.001f && rt.enhance_opencl(src, width, height, src_stride, dst, dst_stride, brightness_factor, contrast_factor)) {
        result = lt::OK;
        if (out != nullptr) {
            out->backend_flags = lt::BACKEND_CPU | lt::BACKEND_OPENCL;
            lt::write_public_message(out, "Enhancement über OpenCL-Kernel");
        }
    } else {
        result = lt::enhance_cpu(src, width, height, src_stride, dst, dst_stride, brightness_factor, contrast_factor, sharpen_amount);
        if (out != nullptr) {
            lt::write_public_message(out, "Enhancement über deterministische C++-CPU-Referenz");
        }
    }

    if (out != nullptr) {
        out->status = static_cast<std::uint32_t>(result);
    }
    return result;
}

} // extern C
