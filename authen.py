# 生成20位的UUID, 一共50个, 搞个表
import uuid
def generate_uuids(n=50):
    uuids = [str(uuid.uuid4()).replace('-', '')[:20] for _ in range(n)]
    return uuids

UUIDS=['root_not_delete','c3a1387d57ca45b1a35d', 'c75c6eb151a049d3af17', 'd3ae1960e30a48858b57', '2398ce0a761d450b896b', 'bca47a2b180c42b286f0', 'def3f161b35d4253b858', 'f75edab0477a47e39502', 'e6a97bce6101434cbf9a', '646c51ed7e1f406abfe5', 'e15eb47601ac439a8b63', '39d8e39c9cee490bb320', '4b4f350083f4447899da', '3091fc01bf884d84873e', 'ae7dcb7c14094d5db9b4', 'bde168c8d73f4e12911b', '534ec40e2f644e03b3d8', '7e727a3eb06d4c869350', '5e7a1ce223954ec4a5c8', 'c1c02133077743cc94f4', 'c46958153dcb4e919878', '18afab0ceabd40a98833', '06188da8c6cd4dd3875e', 'fb4eb19858ff4ba2bdc9', 'a45d88baa9af439da275', '6c4fdfb21f4445ec88a9', '91c512b9a3e244f5aaf1', '63bf6642e06841ce9b51', '81a91934763f413d893a', 'c096b2b19ee94486b914', '8815486478fe4dcd8987', '397e1951a28a4a0d8ffe', '614b61fa6ef5410caaa0', '862ef5e911d24db9a89f', '92b87c6ca44146cf811c', 'f04a3d7e7e20459ca716', 'fa5ed0d32f754b76982e', '899f41795efa46af9c72', 'b1badcc58ed144c8a26d', '7c5ff02420514bdbb821', '73b789e92fc84693ada2', 'd764a21bd3bc41f99875', '731496cc98974764bf1c', 'ac9f824f49be4b8eae82', 'e0b5c3b753e24a359c80', 'a748c3702178403fba10', '3388dded5c5d4071b85c', '483d8ce2cad94bc5adfe', 'ab799d03fc3f4beb9861', '03bda39dfff448e8a787', 'f74261836ca24d819a35']

def check_uuid(uuid_to_check):
    return uuid_to_check in UUIDS

if __name__ == "__main__":
    uuid_list = generate_uuids(50)
    print(uuid_list)
    print(check_uuid('c3a1387d57ca45b1a35d'))  # True

