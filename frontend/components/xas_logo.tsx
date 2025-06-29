import Image from 'next/image'
import logo from '@/public/static/drxas_logo.png' // adjust path as needed

export default function Logo(props: Omit<React.ComponentProps<'img'>, 'width' | 'height'>) {
    return (
        <Image
            src={logo}
            alt="Logo"
            width={48}
            height={48}
            {...props}
        />
    )
}