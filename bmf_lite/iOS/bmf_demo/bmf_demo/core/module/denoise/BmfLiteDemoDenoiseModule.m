/*
 * Copyright 2024 Babit Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "BmfLiteDemoDenoiseModule.h"
#include "BmfLiteDemoErrorCode.h"

BMFLITE_DEMO_NAMESPACE_BEGIN

BmfLiteDemoDenoiseModule::BmfLiteDemoDenoiseModule() { denoise_ = nullptr; }

BmfLiteDemoDenoiseModule::~BmfLiteDemoDenoiseModule() {
    if (denoise_ != nullptr) {
        bmf_lite::AlgorithmFactory::releaseAlgorithmInterface(denoise_);
    }
    denoise_ = nullptr;
}

int BmfLiteDemoDenoiseModule::init() {
    denoise_ = bmf_lite::AlgorithmFactory::createAlgorithmInterface();

    bmf_lite::Param init_param;
    init_param.setInt("change_mode",2);
    init_param.setString("instance_id","denoise1");
    init_param.setInt("algorithm_type", 1);

    init_param.setInt("algorithm_version",1);
    
    init_param.setInt("backend",3);
    init_param.setString("library_path", "");

    assert(denoise_->setParam(init_param) == 0);
    
    bmf_lite::Param set_param;
    set_param.setInt("change_mode",5);
    set_param.setString("instance_id","denoise1");
    set_param.setInt("algorithm_type", 0);
    set_param.setInt("algorithm_version", 1);
    assert(denoise_->setParam(set_param) == 0);
    

    HardwareDataInfo hardware_data_info_in;
    hardware_data_info_in.mem_type = MemoryType::kCVPixelBuffer;

    HardwareDataInfo hardware_data_info_out;
    hardware_data_info_out.mem_type = MemoryType::kMultiMetalTexture;

    bmf_lite::HardwareDeviceCreateInfo create_info{bmf_lite::kHWDeviceTypeMTL, NULL};
    std::shared_ptr<bmf_lite::HWDeviceContext> mtl_device_context;
    bmf_lite::HWDeviceContextManager::createHwDeviceContext(&create_info,mtl_device_context);
      
    return 0;
}

int BmfLiteDemoDenoiseModule::process(std::shared_ptr<VideoFrame> data) {
    if (nullptr == data) {
        return BmfLiteErrorCode::VIDEO_FRAME_IS_NIL;
    }
    if (data->eos_) {
        return BmfLiteErrorCode::SUCCESS;
    }
    bmf_lite::HardwareDataInfo hardware_info{};
    hardware_info.internal_format=bmf_lite::BMF_LITE_CV_NV12;
    hardware_info.mem_type=bmf_lite::MemoryType::kCVPixelBuffer;

    bmf_lite::HardwareDeviceCreateInfo create_info{bmf_lite::kHWDeviceTypeMTL, NULL};
    std::shared_ptr<bmf_lite::HWDeviceContext> mtl_device_context;
    bmf_lite::HWDeviceContextManager::createHwDeviceContext(&create_info,mtl_device_context);
    CVPixelBufferRef buf = data->buffer_;
    int w = CVPixelBufferGetWidth(data->buffer_);
    int h = CVPixelBufferGetHeight(data->buffer_);
    std::shared_ptr<bmf_lite::VideoBuffer> video_buffer;

    bmf_lite::VideoBufferManager::createTextureVideoBufferFromExistingData(data->buffer_, w, h, &hardware_info, mtl_device_context, nullptr, video_buffer);

    bmf_lite::VideoFrame videoframe(video_buffer);
    bmf_lite::Param param;
    assert(denoise_->processVideoFrame(videoframe, param) == 0);
    bmf_lite::VideoFrame oframe;
    bmf_lite::Param output_param;
    assert(denoise_->getVideoFrameOutput(oframe, output_param) == 0);
    std::shared_ptr<VideoBuffer> obuf = oframe.buffer();
    CVPixelBufferRef ocv_buf = (CVPixelBufferRef)obuf->data();
    data->setCVPixelBufferRef(ocv_buf);

    return SUCCESS;
}

BMFLITE_DEMO_NAMESPACE_END

