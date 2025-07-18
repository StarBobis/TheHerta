import shutil
import math

from .m_ini_builder import *
from .drawib_model_universal import DrawIBModelUniversal
from ..config.main_config import GlobalConfig
from .m_ini_helper import M_IniHelperV2
from .m_counter import M_Counter
from ..properties.properties_generate_mod import Properties_GenerateMod
from ..migoto.migoto_format import TextureReplace

class M_CTX_IniModel:
    '''
    支持的游戏：
    - 燕云十六声 YYSLS
    - 死或生：沙滩排球
    '''
    drawib_drawibmodel_dict:dict[str,DrawIBModelUniversal] = {}

    # VertexLimitRaise导致的缩进
    vlr_filter_index_indent = ""

    # 贴图filter_index功能
    texture_hash_filter_index_dict = {}


    @classmethod
    def initialzie(cls):
        '''
        You have to call this to clean cache data before generate mod.
        '''
        cls.drawib_drawibmodel_dict = {}
        

        cls.vlr_filter_index_indent = ""

        cls.texture_hash_filter_index_dict = {}
        
    @classmethod
    def add_unity_vs_texture_override_vb_sections(cls,config_ini_builder:M_IniBuilder,commandlist_ini_builder:M_IniBuilder,draw_ib_model:DrawIBModelUniversal):
        # 声明TextureOverrideVB部分，只有使用GPU-PreSkinning时是直接替换hash对应槽位
        d3d11GameType = draw_ib_model.d3d11GameType
        draw_ib = draw_ib_model.draw_ib

        # 只有GPU-PreSkinning需要生成TextureOverrideVB部分，CPU类型不需要
        if not d3d11GameType.GPU_PreSkinning:
            return

        texture_override_vb_section = M_IniSection(M_SectionType.TextureOverrideVB)
        texture_override_vb_section.append("; " + draw_ib + " ----------------------------")
        for category_name in d3d11GameType.OrderedCategoryNameList:
            category_hash = draw_ib_model.import_config.category_hash_dict[category_name]
            category_slot = d3d11GameType.CategoryExtractSlotDict[category_name]

            texture_override_vb_name_suffix = "VB_" + draw_ib + "_" + draw_ib_model.draw_ib_alias + "_" + category_name
            texture_override_vb_section.append("[TextureOverride_" + texture_override_vb_name_suffix + "]")
            texture_override_vb_section.append("hash = " + category_hash)

            
            # (1) 先初始化CommandList
            drawtype_indent_prefix = ""
            if Properties_GenerateMod.position_override_filter_draw_type():
                if category_name == d3d11GameType.CategoryDrawCategoryDict["Position"]:
                    drawtype_indent_prefix = "  "
                    texture_override_vb_section.append("if DRAW_TYPE == 1")
            
            # 如果出现了VertexLimitRaise，Texcoord槽位需要检测filter_index才能替换
            filterindex_indent_prefix = ""
            if Properties_GenerateMod.vertex_limit_raise_add_filter_index():
                if category_name == d3d11GameType.CategoryDrawCategoryDict["Texcoord"]:
                    if cls.vlr_filter_index_indent != "":
                        texture_override_vb_section.append("if vb0 == " + str(3000 + M_Counter.generated_mod_number))
                        filterindex_indent_prefix = "  "

            # 遍历获取所有在当前分类hash下进行替换的分类，并添加对应的资源替换
            for original_category_name, draw_category_name in d3d11GameType.CategoryDrawCategoryDict.items():
                if category_name == draw_category_name:
                    category_original_slot = d3d11GameType.CategoryExtractSlotDict[original_category_name]
                    texture_override_vb_section.append(filterindex_indent_prefix + drawtype_indent_prefix + category_original_slot + " = Resource" + draw_ib + original_category_name)


            if Properties_GenerateMod.position_override_filter_draw_type():
                # 对应if DRAW_TYPE == 1的结束
                if category_name == d3d11GameType.CategoryDrawCategoryDict["Position"]:
                    texture_override_vb_section.append("endif")
            
            if Properties_GenerateMod.vertex_limit_raise_add_filter_index():
                # 对应if vb0 == 3000的结束
                if category_name == d3d11GameType.CategoryDrawCategoryDict["Texcoord"]:
                    if cls.vlr_filter_index_indent != "":
                        texture_override_vb_section.append("endif")
            
            # 分支架构，如果是Position则需提供激活变量
            if category_name == d3d11GameType.CategoryDrawCategoryDict["Position"]:
                if len(draw_ib_model.key_name_mkey_dict.keys()) != 0:
                    texture_override_vb_section.append("$active" + str(M_Counter.generated_mod_number) + " = 1")

            texture_override_vb_section.new_line()


        config_ini_builder.append_section(texture_override_vb_section)

    @classmethod
    def add_unity_vs_texture_override_ib_sections(cls,config_ini_builder:M_IniBuilder,commandlist_ini_builder:M_IniBuilder,draw_ib_model:DrawIBModelUniversal):
        texture_override_ib_section = M_IniSection(M_SectionType.TextureOverrideIB)
        draw_ib = draw_ib_model.draw_ib
        
        d3d11GameType = draw_ib_model.d3d11GameType

        for count_i in range(len(draw_ib_model.import_config.part_name_list)):
            match_first_index = draw_ib_model.import_config.match_first_index_list[count_i]
            part_name = draw_ib_model.import_config.part_name_list[count_i]

            style_part_name = "Component" + part_name

            
            texture_override_name_suffix = "IB_" + draw_ib + "_" + draw_ib_model.draw_ib_alias + "_" + style_part_name

            # 读取使用的IBResourceName，如果读取不到，就使用默认的
            ib_resource_name = ""
            ib_resource_name = draw_ib_model.PartName_IBResourceName_Dict.get(part_name,None)
            

            texture_override_ib_section.append("[TextureOverride_" + texture_override_name_suffix + "]")
            texture_override_ib_section.append("hash = " + draw_ib)
            texture_override_ib_section.append("match_first_index = " + match_first_index)

            if cls.vlr_filter_index_indent != "":
                texture_override_ib_section.append("if vb0 == " + str(3000 + M_Counter.generated_mod_number))

            texture_override_ib_section.append(cls.vlr_filter_index_indent + "handling = skip")

            # If ib buf is emprt, continue to avoid add ib resource replace.
            ib_buf = draw_ib_model.componentname_ibbuf_dict.get("Component " + part_name,None)
            if ib_buf is None or len(ib_buf) == 0:
                # 不导出对应部位时，要写ib = null，否则在部分场景会发生卡顿，原因未知但是这就是解决方案。
                texture_override_ib_section.append("ib = null")
                texture_override_ib_section.new_line()
                continue

            # if ZZZ ,use run = CommandListSkinTexture solve slot check problems.
            if GlobalConfig.gamename == "ZZZ" :
                texture_override_ib_section.append(cls.vlr_filter_index_indent + "run = CommandListSkinTexture")

            
            # 遍历获取所有在当前分类hash下进行替换的分类，并添加对应的资源替换
            for original_category_name, draw_category_name in d3d11GameType.CategoryDrawCategoryDict.items():
                category_original_slot = d3d11GameType.CategoryExtractSlotDict[original_category_name]
                texture_override_ib_section.append(category_original_slot + " = Resource" + draw_ib + original_category_name)


            # Add ib replace
            texture_override_ib_section.append(cls.vlr_filter_index_indent + "ib = " + ib_resource_name)

            # Add slot style texture slot replace.
            if not Properties_GenerateMod.forbid_auto_texture_ini():
                slot_texture_replace_dict:dict[str,TextureReplace] = draw_ib_model.PartName_SlotTextureReplaceDict_Dict.get(part_name,None)
                # It may not have auto texture
                if slot_texture_replace_dict is not None:
                    for slot,texture_replace in slot_texture_replace_dict.items():

                        if texture_replace.style == "Slot":
                            texture_filter_index_indent = ""
                            if Properties_GenerateMod.slot_style_texture_add_filter_index():
                                texture_override_ib_section.append("if " + slot + " == " + str(cls.texture_hash_filter_index_dict[texture_replace.hash]))
                                texture_filter_index_indent = "  "

                            texture_override_ib_section.append(texture_filter_index_indent + cls.vlr_filter_index_indent + slot + " = " + texture_replace.resource_name)

                            if Properties_GenerateMod.slot_style_texture_add_filter_index():
                                texture_override_ib_section.append("endif")

            # 如果不使用GPU-Skinning即为Object类型，此时需要在ib下面替换对应槽位
            if not d3d11GameType.GPU_PreSkinning:
                for category_name in d3d11GameType.OrderedCategoryNameList:
                    category_hash = draw_ib_model.import_config.category_hash_dict[category_name]
                    category_slot = d3d11GameType.CategoryExtractSlotDict[category_name]

                    for original_category_name, draw_category_name in d3d11GameType.CategoryDrawCategoryDict.items():
                        if original_category_name == draw_category_name:
                            category_original_slot = d3d11GameType.CategoryExtractSlotDict[original_category_name]
                            texture_override_ib_section.append(cls.vlr_filter_index_indent + category_original_slot + " = Resource" + draw_ib + original_category_name)


            component_name = "Component " + part_name 
            component_model = draw_ib_model.component_name_component_model_dict[component_name]
            drawindexed_str_list = M_IniHelperV2.get_drawindexed_str_list(component_model.final_ordered_draw_obj_model_list)
            for drawindexed_str in drawindexed_str_list:
                texture_override_ib_section.append(drawindexed_str)
            
            # 补全endif
            if cls.vlr_filter_index_indent:
                texture_override_ib_section.append("endif")
                texture_override_ib_section.new_line()
            
        config_ini_builder.append_section(texture_override_ib_section)

    @classmethod
    def add_unity_vs_texture_override_vlr_section(cls,config_ini_builder:M_IniBuilder,commandlist_ini_builder:M_IniBuilder,draw_ib_model:DrawIBModelUniversal):
        '''
        Add VertexLimitRaise section, UnityVS style.
        Only Unity VertexShader GPU-PreSkinning use this.

        格式问题：
        override_byte_stride = 40
        override_vertex_count = 14325
        由于这个格式并未添加到CommandList的解析中，所以没法单独写在CommandList里，只能写在TextureOverride下面
        所以我们这个VertexLimitRaise部分直接整体写入CommandList.ini中

        这个部分由于有一个Hash值，所以如果需要加密Mod并且让Hash值修复脚本能够运作的话，
        可以在最终制作完成Mod后，手动把这个VertexLimitRaise部分放到Config.ini中
        '''
        d3d11GameType = draw_ib_model.d3d11GameType
        draw_ib = draw_ib_model.draw_ib
        if d3d11GameType.GPU_PreSkinning:
            vertexlimit_section = M_IniSection(M_SectionType.TextureOverrideVertexLimitRaise)
            

            vertexlimit_section_name_suffix =  draw_ib + "_" + draw_ib_model.draw_ib_alias + "_VertexLimitRaise"
            vertexlimit_section.append("[TextureOverride_" + vertexlimit_section_name_suffix + "]")
            vertexlimit_section.append("hash = " + draw_ib_model.import_config.vertex_limit_hash)
            
            if Properties_GenerateMod.vertex_limit_raise_add_filter_index():
                # 用户可能已经习惯了3000
                vertexlimit_section.append("filter_index = " + str(3000 + M_Counter.generated_mod_number))
                cls.vlr_filter_index_indent = "  "

            vertexlimit_section.append("override_byte_stride = " + str(d3d11GameType.CategoryStrideDict["Position"]))
            vertexlimit_section.append("override_vertex_count = " + str(draw_ib_model.draw_number))
            vertexlimit_section.append("uav_byte_stride = 4")

            vertexlimit_section.new_line()

            commandlist_ini_builder.append_section(vertexlimit_section)

    @classmethod
    def add_unity_vs_resource_vb_sections(cls,ini_builder,draw_ib_model:DrawIBModelUniversal):
        '''
        Add Resource VB Section
        '''
        resource_vb_section = M_IniSection(M_SectionType.ResourceBuffer)
        for category_name in draw_ib_model.d3d11GameType.OrderedCategoryNameList:
            resource_vb_section.append("[Resource" + draw_ib_model.draw_ib + category_name + "]")
            resource_vb_section.append("type = Buffer")

            resource_vb_section.append("stride = " + str(draw_ib_model.d3d11GameType.CategoryStrideDict[category_name]))
            
            resource_vb_section.append("filename = Buffer/" + draw_ib_model.draw_ib + "-" + category_name + ".buf")
            # resource_vb_section.append(";VertexCount: " + str(draw_ib_model.draw_number))
            resource_vb_section.new_line()
        
        '''
        Add Resource IB Section

        We default use R32_UINT because R16_UINT have a very small number limit.
        '''

        for partname, ib_filename in draw_ib_model.PartName_IBBufferFileName_Dict.items():
            ib_resource_name = draw_ib_model.PartName_IBResourceName_Dict.get(partname,None)
            resource_vb_section.append("[" + ib_resource_name + "]")
            resource_vb_section.append("type = Buffer")
            resource_vb_section.append("format = DXGI_FORMAT_R32_UINT")
            resource_vb_section.append("filename = Buffer/" + ib_filename)
            resource_vb_section.new_line()

        ini_builder.append_section(resource_vb_section)


    @classmethod
    def add_resource_texture_sections(cls,ini_builder,draw_ib_model:DrawIBModelUniversal):
        '''
        Add texture resource.
        只有槽位风格贴图会用到，因为Hash风格贴图有专门的方法去声明这个。
        '''
        if Properties_GenerateMod.forbid_auto_texture_ini():
            return 
        
        resource_texture_section = M_IniSection(M_SectionType.ResourceTexture)
        for resource_name, texture_filename in draw_ib_model.TextureResource_Name_FileName_Dict.items():
            if "_Slot_" in texture_filename:
                resource_texture_section.append("[" + resource_name + "]")
                resource_texture_section.append("filename = Texture/" + texture_filename)
                resource_texture_section.new_line()

        ini_builder.append_section(resource_texture_section)


    @classmethod
    def add_unity_cs_texture_override_vb_sections(cls,config_ini_builder:M_IniBuilder,commandlist_ini_builder:M_IniBuilder,draw_ib_model:DrawIBModelUniversal):
        # 声明TextureOverrideVB部分，只有使用GPU-PreSkinning时是直接替换hash对应槽位
        d3d11GameType = draw_ib_model.d3d11GameType
        draw_ib = draw_ib_model.draw_ib

        if d3d11GameType.GPU_PreSkinning:
            texture_override_vb_section = M_IniSection(M_SectionType.TextureOverrideVB)
            texture_override_vb_section.append("; " + draw_ib + " ----------------------------")
            for category_name in d3d11GameType.OrderedCategoryNameList:
                category_hash = draw_ib_model.category_hash_dict[category_name]
                category_slot = d3d11GameType.CategoryExtractSlotDict[category_name]
                texture_override_vb_namesuffix = "VB_" + draw_ib + "_" + draw_ib_model.draw_ib_alias + "_" + category_name

                if GlobalConfig.gamename == "HSR":
                    if category_name == "Position":
                        texture_override_vb_section.append("[TextureOverride_" + texture_override_vb_namesuffix + "_VertexLimitRaise]")
                        texture_override_vb_section.append("override_byte_stride = " + str(d3d11GameType.CategoryStrideDict["Position"]))
                        texture_override_vb_section.append("override_vertex_count = " + str(draw_ib_model.draw_number))
                        texture_override_vb_section.append("uav_byte_stride = 4")
                    else:
                        texture_override_vb_section.append("[TextureOverride_" + texture_override_vb_namesuffix + "]")
                else:
                    texture_override_vb_section.append("[TextureOverride_" + texture_override_vb_namesuffix + "]")
                texture_override_vb_section.append("hash = " + category_hash)
                


                # 如果出现了VertexLimitRaise，Texcoord槽位需要检测filter_index才能替换
                filterindex_indent_prefix = ""
                if category_name == d3d11GameType.CategoryDrawCategoryDict["Texcoord"]:
                    if cls.vlr_filter_index_indent != "":
                        texture_override_vb_section.append("if vb0 == " + str(3000 + M_Counter.generated_mod_number))

                # 遍历获取所有在当前分类hash下进行替换的分类，并添加对应的资源替换
                for original_category_name, draw_category_name in d3d11GameType.CategoryDrawCategoryDict.items():
                    if category_name == draw_category_name:
                        if original_category_name == "Position":
                            texture_override_vb_section.append("cs-cb0 = Resource_" + draw_ib + "_VertexLimit")

                            position_category_slot = d3d11GameType.CategoryExtractSlotDict["Position"]
                            blend_category_slot = d3d11GameType.CategoryExtractSlotDict["Blend"]
                            # print(position_category_slot)

                            texture_override_vb_section.append(position_category_slot + " = Resource" + draw_ib + "Position")
                            texture_override_vb_section.append(blend_category_slot + " = Resource" + draw_ib + "Blend")

                            texture_override_vb_section.append("handling = skip")

                            dispatch_number = int(math.ceil(draw_ib_model.draw_number / 64)) + 1
                            texture_override_vb_section.append("dispatch = " + str(dispatch_number) + ",1,1")
                        elif original_category_name != "Blend":
                            category_original_slot = d3d11GameType.CategoryExtractSlotDict[original_category_name]
                            texture_override_vb_section.append(filterindex_indent_prefix  + category_original_slot + " = Resource" + draw_ib + original_category_name)

                # 对应if vb0 == 3000的结束
                if category_name == d3d11GameType.CategoryDrawCategoryDict["Texcoord"]:
                    if cls.vlr_filter_index_indent != "":
                        texture_override_vb_section.append("endif")
                
                # 分支架构，如果是Position则需提供激活变量
                if category_name == d3d11GameType.CategoryDrawCategoryDict["Position"]:
                    if draw_ib_model.key_number != 0:
                        texture_override_vb_section.append("$active" + str(M_Counter.generated_mod_number) + " = 1")

                texture_override_vb_section.new_line()
            config_ini_builder.append_section(texture_override_vb_section)
            

    @classmethod
    def add_texture_filter_index(cls,ini_builder:M_IniBuilder):
        if not Properties_GenerateMod.slot_style_texture_add_filter_index():
            return 

        filter_index_count = 0
        for draw_ib, draw_ib_model in cls.drawib_drawibmodel_dict.items():
            for partname,slot_texture_replace_dict in draw_ib_model.PartName_SlotTextureReplaceDict_Dict.items():
                for slot, texture_replace in slot_texture_replace_dict.items():
                    if texture_replace.hash in cls.texture_hash_filter_index_dict:
                        continue
                    else:
                        filter_index = 6000 + filter_index_count
                        filter_index_count = filter_index_count + 1
                        cls.texture_hash_filter_index_dict[texture_replace.hash] = filter_index
        

        texture_filter_index_section = M_IniSection(M_SectionType.TextureOverrideTexture)
        for hash_value, filter_index in cls.texture_hash_filter_index_dict.items():
            texture_filter_index_section.append("[TextureOverride_Texture_" + hash_value + "]")
            texture_filter_index_section.append("hash = " + hash_value)
            texture_filter_index_section.append("filter_index = " + str(filter_index))
            texture_filter_index_section.new_line()

        ini_builder.append_section(texture_filter_index_section)

    @classmethod
    def generate_unity_vs_config_ini(cls):
        '''
        Supported Games:
        - Genshin Impact
        - Honkai Impact 3rd
        - Honkai StarRail
        - Zenless Zone Zero
        - Bloody Spell
        - Unity-CPU-PreSkinning (All DX11 Unity games who allow 3Dmigoto inject, mostly used by GF2 now.)
        '''
        config_ini_builder = M_IniBuilder()

        M_IniHelperV2.generate_hash_style_texture_ini(ini_builder=config_ini_builder,drawib_drawibmodel_dict=cls.drawib_drawibmodel_dict)


        if Properties_GenerateMod.slot_style_texture_add_filter_index():
            cls.add_texture_filter_index(ini_builder= config_ini_builder)

        for draw_ib, draw_ib_model in cls.drawib_drawibmodel_dict.items():

            # 按键开关与按键切换声明部分
            M_IniHelperV2.add_switchkey_constants_section(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)
            M_IniHelperV2.add_switchkey_present_section(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)
            M_IniHelperV2.add_switchkey_sections(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model) 
    
            if GlobalConfig.gamename != "YYSLS":
                cls.add_unity_vs_texture_override_vlr_section(config_ini_builder=config_ini_builder,commandlist_ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)
            # cls.add_unity_vs_texture_override_vb_sections(config_ini_builder=config_ini_builder,commandlist_ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)
            cls.add_unity_vs_texture_override_ib_sections(config_ini_builder=config_ini_builder,commandlist_ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)
            cls.add_unity_vs_resource_vb_sections(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)
            cls.add_resource_texture_sections(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)

            M_IniHelperV2.move_slot_style_textures(draw_ib_model=draw_ib_model)

            M_Counter.generated_mod_number = M_Counter.generated_mod_number + 1

        config_ini_builder.save_to_file(GlobalConfig.path_generate_mod_folder() + GlobalConfig.workspacename + ".ini")




