
module(..., package.seeall)

local util = require 'tundra.util'
local boot = require 'tundra.boot'
local decl = require 'tundra.decl'
local path = require 'tundra.path'
local nodegen = require "tundra.nodegen"
local environment = require "tundra.environment"

local _mt_multi = nodegen.create_eval_subclass {}
local _mt_merge = nodegen.create_eval_subclass {}

-- Utility function to compute a suitable filename under $(SRCGENDIR) to
-- generate a file from a given source file.
local function make_generated_filename(env, src_fn, suffix)
	local object_fn

	local src_suffix = path.get_extension(src_fn):sub(2)

    -- Drop leading $(SRCGENDIR) in the input filename, in case a
    -- generated file is used to generate another file.
	do
		local pname = src_fn:match("^%$%(BLOBGENDIR%)[/\\](.*)$")
		if pname then
			object_fn = pname
		else
			object_fn = src_fn
		end
	end

	-- Replace ".." with "dotdot" to avoid creating files outside the
	-- object directory.
    local relative_name = path.drop_suffix(object_fn:gsub("%.%.", "dotdot"))
    return "$(BLOBGENDIR)/" .. relative_name .. suffix
end

local function get_scanner(env)
	local function new_scanner()
		local paths = util.map(env:get_list("BLOBPATH"), function (v) return env:interpolate(v) end)
		local args = {
			Keywords = { "import" },
			RequireWhitespace = 0,
			UseSeparators = 1,
			BareMeansSystem = 0,
		}
		return boot.GlobalEngine:make_generic_scanner(paths, args)
	end
	return assert(new_scanner())
end

function _mt_merge:create_dag(env, args, deps)
    -- Merge inputs into named output file.
    local auxstr = ''
    local outputs = { "$(OBJECTDIR)/_generated/" .. args.OutName }
    if args.AuxName then
        local v = '$(OBJECTDIR)/_generated/' .. args.AuxName
        outputs[#outputs + 1] = v
        auxstr = '-a ' .. v .. ' '
    end
    return env:make_node {
        Label = "BlobC $(@)",
        Action = "$(BLOBC) $(BLOBPATH:p-I) -m -l " .. args.Language .. " -o $(@:[1]) " .. auxstr ..  "$(<)",
        Pass = args.Pass,
        Dependencies = deps,
        InputFiles = args.Sources,
        OutputFiles = outputs,
        Scanner = get_scanner(env),
    }
end

function _mt_multi:create_dag(env, args, deps)
    -- Implicitly generate output names, don't merge inputs.
    local ext, aux_ext
    if args.Language == "c" then
        ext = ".h"
        aux_ext = ".c"
    elseif args.Language == "csharp" then
        ext = ".cs"
    elseif args.Language == "m68k" then
        ext = ".i"
    else
        error("unsupported language " .. args.Language)
    end

    if #args.Sources > 1 then
        error("BlobCt supports a single source file only")
    end

    local outputs = { make_generated_filename(env, args.Sources[1], ext) }
    local aux_str = ''
    if aux_ext then
        local aux_fn = make_generated_filename(env, args.Sources[1], aux_ext)
        outputs[2] = aux_fn
        aux_str = ' -a ' .. aux_fn
    end
    return env:make_node {
        Label = "BlobC $(@)",
        Action = "$(BLOBC) $(BLOBPATH:p-I) -l " .. args.Language .. aux_str .. " -o $(@:[1]) $(<)",
        Pass = args.Pass,
        Dependencies = deps,
        InputFiles = args.Sources,
        OutputFiles = outputs,
        Scanner = get_scanner(env),
    }
end

local blueprint_multi = {
    Sources = { Type = "source_list", Required = true, ExtensionKey = "BLOBCEXTS" },
    Language = { Type = "string", Required = true },
}

local blueprint_merge = {
    Sources = { Type = "source_list", Required = true, ExtensionKey = "BLOBCEXTS"  },
    Language = { Type = "string", Required = true },
    OutName = { Type = "string", Required = true },
    AuxName = { Type = "string" },
}

nodegen.add_evaluator("BlobCt", _mt_multi, blueprint_multi)
nodegen.add_evaluator("BlobCtMerge", _mt_merge, blueprint_merge)

environment.add_global_setup(function(env)
    env:set_default('BLOBC', 'blobc.py')
    env:set_default('BLOBCEXTS', '.blob')
    env:set_default('BLOBGENDIR', '$(OBJECTDIR)/_blobgen')
    env:set_default('BLOBPATH', {})
end)
