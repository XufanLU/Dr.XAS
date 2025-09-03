
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

export type MaterialSpecimenMap = {
  [materialId: string]: string[] // specimens
}

export function MaterialSpecimenPicker({
  materialSpecimenMap,
  selectedMaterial,
  onMaterialChange,
}: {
  materialSpecimenMap: MaterialSpecimenMap
  selectedMaterial: string
  onMaterialChange: (materialId: string) => void
}) {
  return (
    <div className="flex items-center space-x-2">
      <div className="flex flex-col">
        <Select
          name="Spectrum"
          defaultValue={selectedMaterial}
          onValueChange={onMaterialChange}
        >
          <SelectTrigger className="whitespace-nowrap border-none shadow-none focus:ring-0 px-0 py-0 h-6 text-xs">
            <SelectValue placeholder="select from online spectrum database"/>
          </SelectTrigger>
          <SelectContent side="top">
            <SelectGroup>
              <SelectLabel>Spectrum</SelectLabel>
              {/* No empty value item, placeholder is handled by SelectValue */}
              {Object.keys(materialSpecimenMap).map((materialId) => (
                <SelectItem key={materialId} value={materialId}>
                  <span>{materialId}</span>
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
