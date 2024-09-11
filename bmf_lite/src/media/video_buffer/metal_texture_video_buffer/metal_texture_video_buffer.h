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

#ifndef _BMFLITE_METAL_TEXTURE_VIDEOBUFFER_H_
#define _BMFLITE_METAL_TEXTURE_VIDEOBUFFER_H_

#include "media/video_buffer/hardware_device_context.h"
#include "media/video_buffer/video_buffer.h"

namespace bmf_lite {

class MetalTextureVideoBufferImpl;
class MetalTextureVideoBuffer : public VideoBuffer {
  public:
    MetalTextureVideoBuffer(void *texture_id, int width, int height,
                            HardwareDataInfo hardware_data_info,
                            std::shared_ptr<HWDeviceContext> device_context);
    ~MetalTextureVideoBuffer();
    std::shared_ptr<HWDeviceContext> getHWDeviceContext();
    int width();
    int height();
    HardwareDataInfo hardwareDataInfo();
    void *data();
    MemoryType memoryType() { return MemoryType::kMetalTexture; }
    // void* texture_id_;
    std::shared_ptr<MetalTextureVideoBufferImpl> impl_;
};

} // namespace bmf_lite
#endif // _BMFLITE_METAL_TEXTURE_VIDEOBUFFER_H_