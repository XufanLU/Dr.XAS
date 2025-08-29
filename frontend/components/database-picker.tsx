import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import databases, { DatabaseId, Databases } from '@/lib/database'
import { LLMModel, LLMModelConfig } from '@/lib/models'
import { TemplateId, Templates } from '@/lib/templates'
import 'core-js/features/object/group-by.js'
import { Sparkles } from 'lucide-react'
import Image from 'next/image'

export function DataBasePicker({
  databases,
  selectedDatabase,
  onSelectedDatabaseChange
}: {
  databases: Databases
  selectedDatabase: 'auto' | DatabaseId
  onSelectedDatabaseChange: (database: 'auto' | DatabaseId) => void
}) {

  return (
    <div className="flex items-center space-x-2">
      <div className="flex flex-col">
        <Select
          name="database"
          defaultValue={selectedDatabase}
          onValueChange={onSelectedDatabaseChange}
        >
          <SelectTrigger className="whitespace-nowrap border-none shadow-none focus:ring-0 px-0 py-0 h-6 text-xs">
            <SelectValue placeholder="Select a mode"/>
          </SelectTrigger>
          <SelectContent side="top">
            <SelectGroup>
              <SelectLabel>cif source</SelectLabel>
              <SelectItem value="auto">
                <div className="flex items-center space-x-2">
                  {/* <Sparkles
                    className="flex text-[#a1a1aa]"
                    width={14}
                    height={14}
                  /> */}
                  <span>material database</span>
                </div>
              </SelectItem>
              {Object.entries(databases).map(([templateId, template]) => (
                <SelectItem key={templateId} value={templateId}>
                  <div className="flex items-center space-x-2">
                    {/* <Image
                      className="flex"
                      src={`/thirdparty/templates/${templateId}.svg`}
                      alt={templateId}
                      width={14}
                      height={14}
                    /> */}
                    <span>{template.name}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
