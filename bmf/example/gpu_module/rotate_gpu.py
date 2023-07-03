import re
from math import pi, cos, tan, sqrt
import numpy

from bmf import *
import hmp
from cuda import cuda
import cv2, cvcuda
import torch

import pdb

class rotate_gpu(Module):
    def __get_algo(self, algo_str):
        return {
            'area': cvcuda.Interp.AREA,
            'cubic': cvcuda.Interp.CUBIC,
            'linear': cvcuda.Interp.LINEAR,
            'nearest': cvcuda.Interp.NEAREST
        }.get(algo_str, cvcuda.Interp.LINEAR)
    # TODO: Add radians as defalut rotation
    def __get_rotation(self, option):
        self.angle_deg = 0
        # self.shift = None
        self.center = None
        self.scale = 1
        self.algo = cvcuda.Interp.LINEAR
        if 'angle' in option.keys():
            self.angle_deg = eval(option['angle'].lower()) * 180 / pi
        if 'angle_deg' in option.keys():
            self.angle_deg = option['angle_deg']
        if 'center' in option.keys():
            split = re.split('\*|x|,|:', option['center'])
            self.center = (int(split[0]), int(split[1]))
        if 'scale' in option.keys():
            self.scale = self.__get_algo(option['scale'])
        if 'algo' in option.keys():
            self.algo = self.__get_algo(option['algo'])

    def __init__(self, node, option=None):
        self.node_ = node
        self.option_ = option
        self.eof_received_ = False
        # if 'direction' in option.keys():
        #     self.flip_code = self.__get_direction(option['direction'])
        #     if self.flip_code is None:
        #         Log.log(LogLevel.ERROR, "Invalid flip code")
        # else:
        #     Log.log(LogLevel.ERROR, "Flip direction specified")
        self.__get_rotation(option)
        # self.uv_tensor_out = torch.empty((2, self.h // 2, self.w // 2), dtype=torch.uint8, device='cuda')

        self.i420info = hmp.PixelInfo(hmp.PixelFormat.kPF_YUV420P, hmp.ColorSpace.kCS_BT470BG, hmp.ColorRange.kCR_MPEG)
        self.u420info = hmp.PixelInfo(hmp.PixelFormat.kPF_YUV420P10LE, hmp.ColorSpace.kCS_BT2020_CL, hmp.ColorRange.kCR_MPEG)
        if self.center is not None:
            rot_mat = cv2.getRotationMatrix2D(self.center, self.angle_deg, self.scale)
            self.rot_tensor = torch.tensor(rot_mat, dtype=torch.double, device='cuda')
        # self.i420_out = hmp.Frame(self.w, self.h, self.i420info, device='cuda')
        self.i420_out = None
        self.pinfo_map = {hmp.PixelFormat.kPF_NV12: self.i420info,
                          hmp.PixelFormat.kPF_P010LE: self.u420info}
        # self.shift = torch.ones((4,2), dtype=torch.double, device='cuda') * self.shift_tensor
        anglet = torch.ones((4,), dtype=torch.double, device='cuda') * self.angle_deg
        # self.cvshift = cvcuda.as_tensor(shift)
        self.cvangle = cvcuda.as_tensor(anglet)

    def process(self, task):
        
        # get input and output packet queue
        input_queue = task.get_inputs()[0]
        output_queue = task.get_outputs()[0]

        # add all input frames into frame cache
        while not input_queue.empty():
            in_pkt = input_queue.get()

            if in_pkt.timestamp == Timestamp.EOF:
                # we should done all frames processing in following loop
                self.eof_received_ = True
                continue

            in_frame = in_pkt.get(VideoFrame)

            if (in_frame.frame().device() == hmp.Device('cpu')):
                in_frame = in_frame.cuda()
            tensor_list = in_frame.frame().data()
            frame_out = hmp.Frame(in_frame.width, in_frame.height, in_frame.frame().pix_info(), device='cuda')
            # self.i420_out = hmp.Frame(in_frame.width, in_frame.height, self.i420info, device='cuda')

            out_list = frame_out.data()
            stream = hmp.current_stream(hmp.kCUDA)
            cvstream = cvcuda.cuda.as_stream(stream.handle())

            # if (in_frame.frame().format() == hmp.PixelFormat.kPF_NV12 or
            #     in_frame.frame().format() == hmp.PixelFormat.kPF_P010LE or
            #     in_frame.frame().format() == hmp.PixelFormat.kPF_YUV420P or
            #     in_frame.frame().format() == hmp.PixelFormat.kPF_YUV420P10):
            
            if (self.center is None):
                # self.rot_tensor = torch.tensor((in_frame.width // 2, in_frame.height // 2), dtype=torch.double, device='cuda')
                # xform = torch.ones((4,2), dtype=torch.double, device='cuda') * self.rot_tensor
                # cvshift = cvcuda.as_tensor(self.shift)
                center = (in_frame.width // 2, in_frame.height // 2)
                center = numpy.ones((4, 2), dtype=int) * numpy.array((in_frame.width // 2, in_frame.height // 2), dtype=int)
                # rot_mat = cv2.getRotationMatrix2D((in_frame.width // 2, in_frame.height // 2), self.angle_deg, self.scale)

            # deal with nv12 special case
            if (in_frame.frame().format() == hmp.PixelFormat.kPF_NV12 or
                in_frame.frame().format() == hmp.PixelFormat.kPF_P010LE):
                cvimg_batch = cvcuda.ImageBatchVarShape(3)
                cvimg_batch_out = cvcuda.ImageBatchVarShape(3)

                # self.shift = tuple(sh // 2 for sh in self.shift)
                center[1:3] //= 2
                xform = numpy.zeros((4, 6), dtype='float32')
                xform[:] = [cv2.getRotationMatrix2D(c.astype(float), self.angle_deg, self.scale).astype('float32').flatten() for c in center]
                # xform = cv2.getRotationMatrix2D(center, self.angle_deg, self.scale).float().flatten()
                # xform[1:3] = xform[1:3] // 2
                cvxform = cvcuda.as_tensor(hmp.from_numpy(xform).cuda())

                # in_420 = hmp.Frame(in_frame.width, in_frame.height, self.i420info, device='cuda')
                pinfo = self.pinfo_map[in_frame.frame().format()]
                in_420 = hmp.Frame(in_frame.width, in_frame.height, pinfo, device='cuda')
                out_420 = hmp.Frame(in_frame.width, in_frame.height, pinfo, device='cuda')
                hmp.img.yuv_to_yuv(in_420.data(), in_frame.frame().data(), pinfo, in_frame.frame().pix_info())
                # in_list = [x.torch() for x in in_420.data()]
                # out_list = [x.torch().zero_() for x in out_420.data()]
                in_list = in_420.data()
                out_list = out_420.data()

                fill = numpy.array((0, 127, 127))
                torch.from_dlpack(out_list[0])[:] = fill[0]
                torch.from_dlpack(out_list[1])[:] = fill[1]
                torch.from_dlpack(out_list[2])[:] = fill[2]
                cvimg_batch.pushback([cvcuda.as_image(x) for x in in_list])
                cvimg_batch_out.pushback([cvcuda.as_image(x) for x in out_list])

                # shift = torch.ones((3,2), dtype=torch.double, device='cuda') * self.shift_tensor
                # anglet = torch.ones((3,), dtype=torch.double, device='cuda') * self.angle_deg
                # cvshift = cvcuda.as_tensor(shift)
                # cvangle = cvcuda.as_tensor(anglet)
                # pdb.set_trace()
                cvcuda.warp_affine_into(cvimg_batch_out, cvimg_batch,
                                        xform=cvxform, flags=self.algo,
                                        border_mode=cvcuda.Border.CONSTANT, border_value=fill.astype('float32'),
                                        stream=cvstream)
                # cvcuda.rotate_into(cvimg_batch_out, cvimg_batch, 
                #                    angle_deg=self.cvangle, shift=cvshift,
                #                    interpolation=self.algo, stream=cvstream)

                hmp.img.yuv_to_yuv(frame_out.data(), out_420.data(), frame_out.pix_info(), out_420.pix_info())

            # other pixel formats, e.g. yuv420, rgb
            else:
                cvimg_batch = cvcuda.ImageBatchVarShape(in_frame.frame().nplanes())
                cvimg_batch_out = cvcuda.ImageBatchVarShape(in_frame.frame().nplanes())
                # t3 = torch.ones((in_frame.frame().nplanes(),), dtype=torch.double, device='cuda') * self.flip_code
                if (in_frame.frame().format() == hmp.PixelFormat.kPF_YUV420P or
                    in_frame.frame().format() == hmp.PixelFormat.kPF_YUV420P10):
                    center[1:3] //= 2
                    xform = numpy.zeros((4, 6), dtype='float32')
                    xform[:] = [cv2.getRotationMatrix2D(c.astype(float), self.angle_deg, self.scale).astype('float32').flatten() for c in center]
                    # xform = cv2.getRotationMatrix2D(center, self.angle_deg, self.scale).float().flatten()
                    # xform[1:3] = xform[1:3] // 2
                    cvxform = cvcuda.as_tensor(hmp.from_numpy(xform).cuda())

                fill = numpy.array((0, 127, 127))
                for t, f in zip(tensor_list, out_list):
                    cvimg = cvcuda.as_image(t)
                    cvimg_out = cvcuda.as_image(f)
                    cvimg_batch.pushback(cvimg)
                    cvimg_batch_out.pushback(cvimg_out)

                cvcuda.warp_affine_into(cvimg_batch_out, cvimg_batch,
                                        xform=cvxform, flags=self.algo,
                                        border_mode=cvcuda.Border.CONSTANT, border_value=fill.astype('float32'),
                                        stream=cvstream)
                # cvcuda.rotate_into(cvimg_batch_out, cvimg_batch, 
                #                    angle_deg=self.cvangle, shift=cvshift, 
                #                    interpolation=self.algo, stream=cvstream)
            
            videoframe_out = VideoFrame(frame_out)
            videoframe_out.pts = in_frame.pts
            videoframe_out.time_base = in_frame.time_base
            out_pkt = Packet(videoframe_out)
            out_pkt.timestamp = videoframe_out.pts
            output_queue.put(out_pkt)

        if self.eof_received_:
            output_queue.put(Packet.generate_eof_packet())
            Log.log_node(LogLevel.DEBUG, self.node_,
                         'output stream', 'done')
            task.set_timestamp(Timestamp.DONE)

        return ProcessResult.OK